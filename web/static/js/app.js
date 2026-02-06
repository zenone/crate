import { API } from './api.js';
import { setApiBadge, showFiles, toast, getSelectedMp3Paths, updateRowMetadata } from './ui.js';

const state = {
  directory: null,
  contents: null, // response from /api/directory/list
  filterText: '',
  sortMode: 'name-asc',
  lastOperationId: null,
  lastUndoSessionId: null,
};

function $(id) {
  return document.getElementById(id);
}

async function refreshHealth() {
  try {
    await API.health();
    setApiBadge('ok', 'Connected');
  } catch (e) {
    console.error(e);
    setApiBadge('error', 'Disconnected');
  }
}

function setHidden(el, hidden) {
  if (!el) return;
  el.classList.toggle('hidden', !!hidden);
}

function updateActionButtons() {
  const previewBtn = $('preview-btn');
  const renameBtn = $('rename-now-btn');
  const floatingBar = $('floating-action-bar');
  const floatingSel = $('floating-selection-count');

  const anyMp3 = document.querySelectorAll('input.file-select:not(:disabled)').length > 0;
  const selected = getSelectedMp3Paths();

  if (previewBtn) previewBtn.disabled = !anyMp3;
  if (renameBtn) renameBtn.disabled = selected.length === 0;

  if (floatingSel) {
    if (selected.length > 0) {
      floatingSel.textContent = `${selected.length} file${selected.length === 1 ? '' : 's'} selected`;
    } else {
      floatingSel.textContent = anyMp3 ? 'Select files to rename' : '0 files selected';
    }
  }
  if (floatingBar) {
    // Keep actions discoverable: show bar when there are MP3s loaded.
    setHidden(floatingBar, !anyMp3);
  }
}

function applyFilterSort(files) {
  let out = [...files];

  const q = (state.filterText || '').trim().toLowerCase();
  if (q) {
    out = out.filter((f) => {
      const name = (f.name || '').toLowerCase();
      const md = f.metadata || {};
      const artist = String(md.artist || '').toLowerCase();
      const title = String(md.title || '').toLowerCase();
      return name.includes(q) || artist.includes(q) || title.includes(q);
    });
  }

  const mode = state.sortMode || 'name-asc';
  const cmpStr = (a, b) => String(a ?? '').toLowerCase().localeCompare(String(b ?? '').toLowerCase());
  const cmpNum = (a, b) => (Number(a ?? 0) - Number(b ?? 0));

  out.sort((a, b) => {
    switch (mode) {
      case 'name-asc': return cmpStr(a.name, b.name);
      case 'name-desc': return -cmpStr(a.name, b.name);
      case 'modified-desc': return -cmpNum(a.modified_time, b.modified_time);
      case 'modified-asc': return cmpNum(a.modified_time, b.modified_time);
      case 'size-desc': return -cmpNum(a.size, b.size);
      case 'size-asc': return cmpNum(a.size, b.size);
      // Metadata sorts (may be absent; keep stable-ish)
      case 'bpm-asc': return cmpNum(a.metadata?.bpm, b.metadata?.bpm) || cmpStr(a.name, b.name);
      case 'bpm-desc': return -cmpNum(a.metadata?.bpm, b.metadata?.bpm) || cmpStr(a.name, b.name);
      case 'track-asc': return cmpNum(a.metadata?.track, b.metadata?.track) || cmpStr(a.name, b.name);
      default: return cmpStr(a.name, b.name);
    }
  });

  return out;
}

function renderCounts({ totalFiles, mp3Count, shownCount }) {
  const fileCount = $('file-count');
  const mp3El = $('mp3-count');
  const filtered = $('filtered-count');

  if (fileCount) fileCount.textContent = `${totalFiles} files`;
  if (mp3El) mp3El.textContent = `${mp3Count} MP3s`;

  if (filtered) {
    if (shownCount != null && shownCount !== mp3Count) {
      filtered.textContent = `${shownCount} shown`;
      setHidden(filtered, false);
    } else {
      setHidden(filtered, true);
    }
  }
}

function wireTableSelectionHandlers() {
  // per-row checkbox change
  document.querySelectorAll('input.file-select').forEach((el) => {
    el.addEventListener('change', () => {
      // keep select-all in sync
      const enabled = Array.from(document.querySelectorAll('input.file-select:not(:disabled)'));
      const checked = enabled.filter((c) => c.checked);
      const selectAll = $('select-all');
      if (selectAll) {
        selectAll.checked = enabled.length > 0 && checked.length === enabled.length;
        selectAll.indeterminate = checked.length > 0 && checked.length < enabled.length;
      }
      updateActionButtons();
    });
  });

  const selectAll = $('select-all');
  if (selectAll) {
    selectAll.addEventListener('change', () => {
      const enabled = Array.from(document.querySelectorAll('input.file-select:not(:disabled)'));
      for (const cb of enabled) cb.checked = selectAll.checked;
      updateActionButtons();
    });
  }

  updateActionButtons();
}

let metadataAbort = null;

async function loadDirectory(path, recursive = true) {
  const dirInput = $('directory-path');
  if (dirInput) dirInput.value = path;

  state.directory = path;
  const contents = await API.listDirectory(path, recursive);
  state.contents = contents;

  const onlyMp3 = (contents.files || []).filter((f) => f.is_mp3);
  const filteredSorted = applyFilterSort(onlyMp3);

  showFiles({
    ...contents,
    files: filteredSorted,
    total_files: contents.total_files ?? (contents.files || []).length,
    mp3_count: contents.mp3_count ?? onlyMp3.length,
  });

  renderCounts({
    totalFiles: contents.total_files ?? (contents.files || []).length,
    mp3Count: contents.mp3_count ?? onlyMp3.length,
    shownCount: filteredSorted.length,
  });

  wireTableSelectionHandlers();

  // Start metadata loading (best-effort)
  loadMetadataForVisibleFiles(filteredSorted).catch((e) => {
    console.error(e);
  });
}

async function loadMetadataForVisibleFiles(files) {
  const progressEl = $('metadata-progress');
  const barEl = $('metadata-progress-bar');
  const textEl = $('metadata-progress-text');
  const cancelBtn = $('metadata-cancel-btn');
  const currentNameEl = $('metadata-current-file-name');

  // Cancel any prior run
  if (metadataAbort) {
    metadataAbort.abort();
  }
  metadataAbort = new AbortController();

  const mp3s = (files || []).filter((f) => f.is_mp3);
  if (!mp3s.length) {
    if (progressEl) progressEl.classList.add('hidden');
    return;
  }

  let cancelled = false;
  const onCancel = () => {
    cancelled = true;
    metadataAbort?.abort();
    if (progressEl) progressEl.classList.add('hidden');
  };
  cancelBtn?.addEventListener('click', onCancel, { once: true });

  progressEl?.classList.remove('hidden');

  const total = mp3s.length;
  for (let i = 0; i < total; i++) {
    if (cancelled) break;
    const f = mp3s[i];

    const pct = Math.floor(((i) / total) * 100);
    if (barEl) barEl.style.width = `${pct}%`;
    if (textEl) textEl.textContent = `Loading metadata: ${i}/${total} files (${pct}%)`;
    if (currentNameEl) currentNameEl.textContent = f.name;

    // Skip if we already have metadata cached on the object
    if (f.metadata) {
      updateRowMetadata(f.path, f.metadata);
      continue;
    }

    try {
      const resp = await fetch('/api/file/metadata', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ path: f.path, recursive: false, write_metadata: false }),
        signal: metadataAbort.signal,
      });
      if (!resp.ok) {
        // ignore failures per-file
        continue;
      }
      const data = await resp.json();
      const md = data.metadata;
      f.metadata = md;
      const artUrl = API.albumArtUrl(f.path);
      updateRowMetadata(f.path, md, artUrl);
    } catch (e) {
      // Abort = user cancelled; otherwise ignore
      if (e?.name === 'AbortError') break;
    }
  }

  if (barEl) barEl.style.width = '100%';
  if (textEl) textEl.textContent = `Loading metadata: ${total}/${total} files (100%)`;
  if (currentNameEl) currentNameEl.textContent = '—';
  // hide after short delay
  setTimeout(() => progressEl?.classList.add('hidden'), 600);
}

function wireSearchAndSort() {
  const search = $('file-search-input');
  const clearBtn = $('search-clear-btn');
  const sortSel = $('file-sort-select');

  if (sortSel) {
    state.sortMode = sortSel.value || state.sortMode;
    sortSel.addEventListener('change', async () => {
      state.sortMode = sortSel.value;
      if (state.directory) {
        await loadDirectory(state.directory, true);
      }
    });
  }

  function applySearch() {
    state.filterText = search?.value || '';
    if (clearBtn) setHidden(clearBtn, !(state.filterText && state.filterText.length));
    if (state.directory) {
      loadDirectory(state.directory, true).catch((e) => toast(`Search failed: ${e.message}`));
    }
  }

  if (search) {
    search.addEventListener('input', () => applySearch());
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      if (search) search.value = '';
      applySearch();
    });
  }
}

function wireDirectoryBrowserModal() {
  const modal = $('directory-browser-modal');
  const browseBtn = $('browse-btn');
  const dirInput = $('directory-path');

  const listEl = $('browser-list');
  const loadingEl = $('browser-loading');
  const emptyEl = $('browser-empty');
  const pathDisplay = $('browser-path-display');
  const breadcrumbParts = $('breadcrumb-parts');
  const homeBtn = modal?.querySelector('.breadcrumb-home');
  const closeBtn = modal?.querySelector('.modal-close');
  const cancelBtn = $('browser-cancel-btn');
  const selectBtn = $('browser-select-btn');
  const sortSelect = $('browser-sort-select');

  if (!modal || !browseBtn || !listEl || !pathDisplay) return;

  let current = null;
  let selectedPath = null;

  function open() { modal.classList.remove('hidden'); }
  function close() { modal.classList.add('hidden'); }

  function setLoading(isLoading) {
    if (!loadingEl) return;
    loadingEl.classList.toggle('hidden', !isLoading);
  }

  function renderBreadcrumb(parts) {
    if (!breadcrumbParts) return;
    breadcrumbParts.innerHTML = '';

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const btn = document.createElement('button');
      btn.className = 'breadcrumb-part';
      btn.type = 'button';
      btn.textContent = part;

      let path;
      if (i === 0 && part === '/') path = '/';
      else if (parts[0] === '/') path = '/' + parts.slice(1, i + 1).join('/');
      else path = parts.slice(0, i + 1).join('/');

      btn.addEventListener('click', () => browseTo(path).catch(e => toast(`Browse failed: ${e.message}`)));
      breadcrumbParts.appendChild(btn);
    }
  }

  function sortDirs(dirs) {
    const mode = sortSelect?.value || 'name-asc';
    const copy = [...dirs];
    copy.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
    if (mode === 'name-desc') copy.reverse();
    return copy;
  }

  function renderList(resp) {
    listEl.innerHTML = '';

    const dirs = sortDirs(resp.directories || []);
    const hasParent = !!resp.parent_path;

    if (hasParent) {
      const parentItem = document.createElement('div');
      parentItem.className = 'browser-item parent';
      parentItem.innerHTML = `<span class="browser-item-icon">↩︎</span><span class="browser-item-name">..</span>`;
      parentItem.addEventListener('click', () => browseTo(resp.parent_path).catch(e => toast(`Browse failed: ${e.message}`)));
      listEl.appendChild(parentItem);
    }

    for (const d of dirs) {
      const item = document.createElement('div');
      item.className = 'browser-item';
      item.dataset.path = d.path;
      item.innerHTML = `<span class="browser-item-icon">📁</span><span class="browser-item-name"></span>`;
      item.querySelector('.browser-item-name').textContent = d.name;

      item.addEventListener('click', () => {
        browseTo(d.path).catch(e => toast(`Browse failed: ${e.message}`));
      });

      listEl.appendChild(item);
    }

    if (emptyEl) emptyEl.classList.toggle('hidden', (dirs.length + (hasParent ? 1 : 0)) > 0);
  }

  async function browseTo(path) {
    setLoading(true);
    try {
      const resp = await API.browseDirectory(path || null);
      current = resp;
      selectedPath = resp.current_path;
      pathDisplay.value = selectedPath;
      renderBreadcrumb(resp.path_parts || []);
      renderList(resp);
    } finally {
      setLoading(false);
    }
  }

  browseBtn.addEventListener('click', () => {
    open();
    browseTo(dirInput?.value?.trim() || null).catch(e => toast(`Browse failed: ${e.message}`));
  });

  closeBtn?.addEventListener('click', close);
  cancelBtn?.addEventListener('click', close);
  modal.querySelector('.modal-overlay')?.addEventListener('click', close);

  homeBtn?.addEventListener('click', () => browseTo(null).catch(e => toast(`Browse failed: ${e.message}`)));
  sortSelect?.addEventListener('change', () => { if (current) renderList(current); });

  selectBtn?.addEventListener('click', async () => {
    if (!selectedPath) return;
    if (dirInput) dirInput.value = selectedPath;
    close();
    try {
      await loadDirectory(selectedPath, true);
    } catch (e) {
      toast(`Load failed: ${e.message}`);
    }
  });
}

function wireSettingsModal() {
  const modal = $('settings-modal');
  const openBtnTop = $('settings-btn');
  const openBtnBottom = $('settings-btn-bottom');
  const saveBtn = $('settings-save-btn');
  const resetBtn = $('settings-reset-btn');
  const cancelBtn = $('settings-cancel-btn');
  const form = $('settings-form');

  if (!modal || (!openBtnTop && !openBtnBottom)) return;

  const closeEls = modal.querySelectorAll('.modal-close, .modal-overlay');

  function open() {
    modal.classList.remove('hidden');
  }

  function close() {
    modal.classList.add('hidden');
  }

  async function loadIntoForm() {
    try {
      const cfg = await API.getConfig();

      // Populate known fields if present
      const setVal = (id, v) => {
        const el = $(id);
        if (!el) return;
        el.value = v ?? '';
      };
      const setChk = (id, v) => {
        const el = $(id);
        if (!el) return;
        el.checked = !!v;
      };

      setVal('acoustid-api-key', cfg.acoustid_api_key);
      setChk('enable-musicbrainz', cfg.enable_musicbrainz);
      setChk('use-mb-for-all-fields', cfg.use_mb_for_all_fields);

      setChk('auto-detect-bpm', cfg.auto_detect_bpm);
      setChk('auto-detect-key', cfg.auto_detect_key);

      setChk('remember-last-directory', cfg.remember_last_directory);
      setChk('recursive-default', cfg.recursive_default);

      setVal('track-number-padding', cfg.track_number_padding);
      setChk('verify-mode', cfg.verify_mode);

      setChk('enable-smart-detection', cfg.enable_smart_detection);
      setChk('enable-per-album-detection', cfg.enable_per_album_detection);
      setChk('enable-auto-select-albums', cfg.enable_auto_select_albums);
      setChk('enable-auto-apply', cfg.enable_auto_apply);

      setChk('enable-toast-notifications', cfg.enable_toast_notifications);

      const conf = $('confidence-threshold');
      const confVal = $('confidence-threshold-value');
      if (conf) {
        conf.value = String(cfg.confidence_threshold ?? conf.value);
        if (confVal) confVal.textContent = String(conf.value);
      }
    } catch (e) {
      toast(`Failed to load settings: ${e.message}`);
    }
  }

  function collectUpdates() {
    const updates = {};

    const getVal = (id) => {
      const el = $(id);
      return el ? el.value : undefined;
    };
    const getChk = (id) => {
      const el = $(id);
      return el ? !!el.checked : undefined;
    };

    // Only include keys that exist in form (avoid blasting unknown keys)
    updates.acoustid_api_key = getVal('acoustid-api-key');
    updates.enable_musicbrainz = getChk('enable-musicbrainz');
    updates.use_mb_for_all_fields = getChk('use-mb-for-all-fields');

    updates.auto_detect_bpm = getChk('auto-detect-bpm');
    updates.auto_detect_key = getChk('auto-detect-key');

    updates.remember_last_directory = getChk('remember-last-directory');
    updates.recursive_default = getChk('recursive-default');

    const pad = getVal('track-number-padding');
    if (pad !== undefined && pad !== '') updates.track_number_padding = Number(pad);

    updates.verify_mode = getChk('verify-mode');

    updates.enable_smart_detection = getChk('enable-smart-detection');
    updates.enable_per_album_detection = getChk('enable-per-album-detection');
    updates.enable_auto_select_albums = getChk('enable-auto-select-albums');
    updates.enable_auto_apply = getChk('enable-auto-apply');

    updates.enable_toast_notifications = getChk('enable-toast-notifications');

    const conf = $('confidence-threshold');
    if (conf) updates.confidence_threshold = Number(conf.value);

    return updates;
  }

  async function save() {
    try {
      const updates = collectUpdates();
      await API.updateConfig(updates);
      toast('Settings saved');
      close();
    } catch (e) {
      toast(`Save failed: ${e.message}`);
    }
  }

  openBtnTop?.addEventListener('click', () => {
    open();
    loadIntoForm();
  });
  openBtnBottom?.addEventListener('click', () => {
    open();
    loadIntoForm();
  });

  closeEls.forEach((el) => el.addEventListener('click', close));
  cancelBtn?.addEventListener('click', close);

  saveBtn?.addEventListener('click', (e) => {
    e.preventDefault();
    save();
  });

  resetBtn?.addEventListener('click', async (e) => {
    e.preventDefault();
    // Simple behavior: re-fetch config from backend
    await loadIntoForm();
    toast('Settings reloaded');
  });

  // live update label for slider
  const conf = $('confidence-threshold');
  const confVal = $('confidence-threshold-value');
  conf?.addEventListener('input', () => {
    if (confVal) confVal.textContent = String(conf.value);
  });

  // prevent full-page reload on Enter
  form?.addEventListener('submit', (e) => {
    e.preventDefault();
    save();
  });
}

function wirePreviewModal() {
  const previewBtn = $('preview-btn');
  const floatingPreview = $('floating-preview-btn');
  const previewModal = $('preview-modal');
  const previewList = $('preview-list');
  const previewLoading = $('preview-loading');
  const previewEmpty = $('preview-empty');
  const closeEls = previewModal ? previewModal.querySelectorAll('.modal-close, .modal-overlay, #preview-cancel-btn, #preview-empty-close-btn') : [];

  function open() { previewModal?.classList.remove('hidden'); }
  function close() { previewModal?.classList.add('hidden'); }
  closeEls?.forEach((el) => el.addEventListener('click', close));

  async function runPreview() {
    const p = (state.directory || $('directory-path')?.value || '').trim();
    if (!p) return;

    const files = getSelectedMp3Paths();
    const resp = await API.previewRename({ path: p, recursive: false, file_paths: files.length ? files : null });

    const setText = (id, v) => { const el = $(id); if (el) el.textContent = String(v ?? 0); };
    setText('preview-stat-total', resp.total);
    setText('preview-stat-rename', resp.stats?.will_rename);
    setText('preview-stat-skip', resp.stats?.will_skip);
    setText('preview-stat-errors', resp.stats?.errors);

    if (previewList) previewList.innerHTML = '';
    const previews = resp.previews || [];

    if (previewLoading) previewLoading.classList.add('hidden');

    if (!previews.length) {
      previewEmpty?.classList.remove('hidden');
      return;
    }
    previewEmpty?.classList.add('hidden');

    for (const pr of previews) {
      const src = (pr.src || '').split('/').pop();
      const dst = pr.dst ? pr.dst.split('/').pop() : '';
      const status = pr.status;
      const reason = pr.reason || '';

      const row = document.createElement('div');
      row.className = 'preview-item';
      row.innerHTML = `
        <div class="preview-item-main">
          <div class="preview-item-src"></div>
          <div class="preview-item-dst"></div>
        </div>
        <div class="preview-item-meta"></div>
      `;
      row.querySelector('.preview-item-src').textContent = src;
      row.querySelector('.preview-item-dst').textContent = (status === 'will_rename') ? `→ ${dst}` : reason || 'No change';
      row.querySelector('.preview-item-meta').textContent = status;

      previewList.appendChild(row);
    }
  }

  function startPreview() {
    if (previewLoading) previewLoading.classList.remove('hidden');
    previewEmpty?.classList.add('hidden');
    open();
    runPreview().catch((e) => {
      console.error(e);
      toast(`Preview failed: ${e.message}`);
      close();
    });
  }

  previewBtn?.addEventListener('click', startPreview);
  floatingPreview?.addEventListener('click', startPreview);
}

function wireRenameConfirmModal(executeFn, previewFn) {
  const modal = $('rename-confirm-modal');
  const openBtn = $('rename-now-btn');
  const floatingRename = $('floating-rename-btn');
  const closeEls = modal ? modal.querySelectorAll('.modal-close, .modal-overlay, #rename-confirm-cancel-btn') : [];

  const previewBtn = $('rename-confirm-preview-btn');
  const execBtn = $('rename-confirm-execute-btn');

  function open() {
    const count = getSelectedMp3Paths().length;
    const cntEl = $('rename-file-count');
    if (cntEl) cntEl.textContent = String(count);
    modal?.classList.remove('hidden');
  }
  function close() { modal?.classList.add('hidden'); }

  closeEls?.forEach((el) => el.addEventListener('click', close));
  openBtn?.addEventListener('click', () => { if (getSelectedMp3Paths().length) open(); });
  floatingRename?.addEventListener('click', () => { if (getSelectedMp3Paths().length) open(); });

  previewBtn?.addEventListener('click', () => {
    close();
    previewFn();
  });

  execBtn?.addEventListener('click', () => {
    close();
    executeFn();
  });
}

function wireProgressOverlay() {
  const overlay = $('progress-overlay');
  const bar = $('progress-bar');
  const percentEl = $('progress-percent');
  const currentEl = $('progress-current');
  const totalEl = $('progress-total');
  const msgEl = $('progress-message');
  const outputEl = $('progress-output');
  const cancelBtn = $('progress-cancel-btn');
  const doneBtn = $('progress-done-btn');

  function open() {
    overlay?.classList.remove('hidden');
    doneBtn?.classList.add('hidden');
    cancelBtn?.classList.remove('hidden');
  }

  function close() {
    overlay?.classList.add('hidden');
  }

  doneBtn?.addEventListener('click', close);

  return {
    open,
    close,
    set: ({ progress, total, currentFile, message }) => {
      const pct = total > 0 ? Math.floor((progress / total) * 100) : 0;
      if (percentEl) percentEl.textContent = `${pct}%`;
      if (currentEl) currentEl.textContent = String(progress ?? 0);
      if (totalEl) totalEl.textContent = String(total ?? 0);
      if (bar) bar.style.width = `${pct}%`;
      if (msgEl) msgEl.textContent = message || (currentFile ? `Processing: ${currentFile}` : '');
    },
    setOutputHtml: (html) => { if (outputEl) outputEl.innerHTML = html; },
    setDone: () => {
      cancelBtn?.classList.add('hidden');
      doneBtn?.classList.remove('hidden');
    },
    onCancel: (fn) => {
      cancelBtn?.addEventListener('click', fn);
    },
  };
}

function wire() {
  const refreshBtn = $('refresh-btn');
  const dirInput = $('directory-path');

  wireDirectoryBrowserModal();
  wireSearchAndSort();

  refreshBtn?.addEventListener('click', async () => {
    try {
      const p = dirInput?.value?.trim();
      if (!p) return;
      await loadDirectory(p, true);
    } catch (e) {
      toast(`Refresh failed: ${e.message}`);
    }
  });

  wirePreviewModal();
  wireSettingsModal();

  const progress = wireProgressOverlay();

  async function execute() {
    const p = (state.directory || dirInput?.value || '').trim();
    if (!p) return;
    const files = getSelectedMp3Paths();
    if (!files.length) {
      toast('Select at least one MP3');
      return;
    }

    state.lastUndoSessionId = null;

    const r = await API.executeRename({ path: p, file_paths: files, dry_run: false });
    const op = r.operation_id;
    state.lastOperationId = op;

    progress.open();
    progress.set({ progress: 0, total: files.length, currentFile: '', message: 'Starting rename…' });
    progress.setOutputHtml('');

    let cancelled = false;
    progress.onCancel(async () => {
      if (!state.lastOperationId || cancelled) return;
      cancelled = true;
      try {
        await API.cancelOperation(state.lastOperationId);
        toast('Cancellation requested');
      } catch (e) {
        toast(`Cancel failed: ${e.message}`);
      }
    });

    // Poll operation status
    for (let i = 0; i < 240; i++) {
      const st = await API.getOperation(op);

      progress.set({
        progress: st.progress ?? 0,
        total: st.total ?? files.length,
        currentFile: (st.current_file || '').split('/').pop(),
        message: st.status === 'running' ? '' : `Status: ${st.status}`,
      });

      if (st.status === 'completed') {
        const renamed = st.results?.renamed ?? 0;
        const skipped = st.results?.skipped ?? 0;
        const errors = st.results?.errors ?? 0;

        let html = `<div>✅ Completed. Renamed: <strong>${renamed}</strong>, Skipped: <strong>${skipped}</strong>, Errors: <strong>${errors}</strong></div>`;

        if (st.undo_session_id) {
          state.lastUndoSessionId = st.undo_session_id;
          html += `<div style="margin-top:8px;">↩️ <button id="undo-btn" class="btn btn-secondary btn-sm" type="button">Undo</button> <span class="dim">(available ~10 min)</span></div>`;
        }

        progress.setOutputHtml(html);
        progress.setDone();

        // wire undo button if present
        const undoBtn = document.getElementById('undo-btn');
        undoBtn?.addEventListener('click', async () => {
          if (!state.lastUndoSessionId) return;
          try {
            const ur = await API.undoRename(state.lastUndoSessionId);
            toast(ur.message || 'Undo complete');
            // refresh directory view after undo
            if (state.directory) await loadDirectory(state.directory, true);
          } catch (e) {
            toast(`Undo failed: ${e.message}`);
          }
        });

        // refresh directory view after completion
        if (state.directory) await loadDirectory(state.directory, true);
        break;
      }

      if (st.status === 'error' || st.status === 'cancelled') {
        progress.setOutputHtml(`<div>❌ ${st.status}: ${st.error || ''}</div>`);
        progress.setDone();
        break;
      }

      await new Promise((r) => setTimeout(r, 250));
    }
  }

  function startPreview() {
    $('preview-btn')?.click();
  }

  wireRenameConfirmModal(() => execute().catch((e) => toast(`Execute failed: ${e.message}`)), startPreview);

  // Also keep rename available from floating action bar
  $('floating-rename-btn')?.addEventListener('click', () => {
    // modal wired above
  });

  // initial
  updateActionButtons();
}

window.addEventListener('load', async () => {
  setApiBadge('loading', 'Connecting...');
  await refreshHealth();
  wire();

  // initial directory
  try {
    const init = await API._getJson('/api/directory/initial');
    if (init?.path) {
      await loadDirectory(init.path, true);
    }
  } catch {
    // ignore
  }

  setInterval(refreshHealth, 5000);
});
