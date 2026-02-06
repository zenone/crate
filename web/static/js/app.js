import { API } from './api.js';
import { setApiBadge, showFiles, toast, getSelectedMp3Paths } from './ui.js';

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
    floatingSel.textContent = `${selected.length} file${selected.length === 1 ? '' : 's'} selected`;
  }
  if (floatingBar) {
    setHidden(floatingBar, selected.length === 0);
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
