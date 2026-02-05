import { API } from './api.js';
import { setApiBadge, showFiles, toast, getSelectedMp3Paths } from './ui.js';

async function refreshHealth() {
  try {
    await API.health();
    setApiBadge('ok', 'Connected');
  } catch (e) {
    console.error(e);
    setApiBadge('error', 'Disconnected');
  }
}

function updateActionButtons() {
  const previewBtn = document.getElementById('preview-btn');
  const renameBtn = document.getElementById('rename-now-btn');
  const selected = getSelectedMp3Paths();

  // Enable preview if we have any MP3s listed (even if none selected, it can preview all)
  const anyMp3 = document.querySelectorAll('input.file-select:not(:disabled)').length > 0;
  if (previewBtn) previewBtn.disabled = !anyMp3;

  // Enable rename only when at least one file is selected
  if (renameBtn) renameBtn.disabled = selected.length === 0;
}

async function loadDirectory(path, recursive = false) {
  const dirInput = document.getElementById('directory-path');
  if (dirInput) dirInput.value = path;
  const contents = await API.listDirectory(path, recursive);
  showFiles(contents);

  // Wire checkbox changes for selection-driven actions
  document.querySelectorAll('input.file-select').forEach((el) => {
    el.addEventListener('change', updateActionButtons);
  });
  updateActionButtons();
}

function wireDirectoryBrowserModal() {
  const modal = document.getElementById('directory-browser-modal');
  const browseBtn = document.getElementById('browse-btn');
  const dirInput = document.getElementById('directory-path');

  const listEl = document.getElementById('browser-list');
  const loadingEl = document.getElementById('browser-loading');
  const emptyEl = document.getElementById('browser-empty');
  const pathDisplay = document.getElementById('browser-path-display');
  const breadcrumbParts = document.getElementById('breadcrumb-parts');
  const homeBtn = modal?.querySelector('.breadcrumb-home');
  const closeBtn = modal?.querySelector('.modal-close');
  const cancelBtn = document.getElementById('browser-cancel-btn');
  const selectBtn = document.getElementById('browser-select-btn');
  const sortSelect = document.getElementById('browser-sort-select');

  if (!modal || !browseBtn || !listEl || !pathDisplay) return;

  let current = null;
  let selectedPath = null;

  function open() {
    modal.classList.remove('hidden');
  }
  function close() {
    modal.classList.add('hidden');
  }

  function setLoading(isLoading) {
    if (!loadingEl) return;
    loadingEl.classList.toggle('hidden', !isLoading);
  }

  function renderBreadcrumb(parts) {
    if (!breadcrumbParts) return;
    breadcrumbParts.innerHTML = '';

    // Build cumulative paths safely by index
    // Example parts on macOS: ["/", "Users", "szenone", "Music"]
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];

      const btn = document.createElement('button');
      btn.className = 'breadcrumb-part';
      btn.type = 'button';
      btn.textContent = part;

      let path;
      if (i === 0 && part === '/') {
        path = '/';
      } else if (parts[0] === '/') {
        path = '/' + parts.slice(1, i + 1).join('/');
      } else {
        path = parts.slice(0, i + 1).join('/');
      }

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
      parentItem.innerHTML = `
        <span class="browser-item-icon">↩︎</span>
        <span class="browser-item-name">..</span>
      `;
      parentItem.addEventListener('click', () => browseTo(resp.parent_path).catch(e => toast(`Browse failed: ${e.message}`)));
      listEl.appendChild(parentItem);
    }

    for (const d of dirs) {
      const item = document.createElement('div');
      item.className = 'browser-item';
      item.dataset.path = d.path;
      item.innerHTML = `
        <span class="browser-item-icon">📁</span>
        <span class="browser-item-name"></span>
      `;
      item.querySelector('.browser-item-name').textContent = d.name;

      item.addEventListener('click', () => {
        // Single click navigates (web-native feel)
        browseTo(d.path).catch(e => toast(`Browse failed: ${e.message}`));
      });

      listEl.appendChild(item);
    }

    if (emptyEl) {
      emptyEl.classList.toggle('hidden', (dirs.length + (hasParent ? 1 : 0)) > 0);
    }
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

function wire() {
  const refreshBtn = document.getElementById('refresh-btn');
  const dirInput = document.getElementById('directory-path');

  wireDirectoryBrowserModal();

  if (refreshBtn) {
    refreshBtn.addEventListener('click', async () => {
      try {
        const p = dirInput?.value?.trim();
        if (!p) return;
        await loadDirectory(p, true);
      } catch (e) {
        toast(`Refresh failed: ${e.message}`);
      }
    });
  }

  // Preview modal wiring
  const previewBtn = document.getElementById('preview-btn');
  const previewModal = document.getElementById('preview-modal');
  const previewList = document.getElementById('preview-list');
  const previewLoading = document.getElementById('preview-loading');
  const previewEmpty = document.getElementById('preview-empty');
  const previewCloseEls = previewModal ? previewModal.querySelectorAll('.modal-close, .modal-overlay, #preview-cancel-btn, #preview-empty-close-btn') : [];

  function openPreviewModal() {
    previewModal?.classList.remove('hidden');
  }
  function closePreviewModal() {
    previewModal?.classList.add('hidden');
  }
  previewCloseEls?.forEach((el) => el.addEventListener('click', closePreviewModal));

  async function preview() {
    const p = dirInput?.value?.trim();
    if (!p) return;

    const files = getSelectedMp3Paths();
    const resp = await API.previewRename({ path: p, recursive: false, file_paths: files.length ? files : null });

    // Update stats
    const setText = (id, v) => {
      const el = document.getElementById(id);
      if (el) el.textContent = String(v ?? 0);
    };
    setText('preview-stat-total', resp.total);
    setText('preview-stat-rename', resp.stats?.will_rename);
    setText('preview-stat-skip', resp.stats?.will_skip);
    setText('preview-stat-errors', resp.stats?.errors);

    // Render list
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

    openPreviewModal();
  }

  if (previewBtn) {
    previewBtn.addEventListener('click', () => {
      if (previewLoading) previewLoading.classList.remove('hidden');
      previewEmpty?.classList.add('hidden');
      openPreviewModal();
      preview().catch((e) => {
        console.error(e);
        toast(`Preview failed: ${e.message}`);
        closePreviewModal();
      });
    });
  }

  // Wire execute buttons if present
  const floatingPreview = document.getElementById('floating-preview-btn');
  const floatingRename = document.getElementById('floating-rename-btn');
  const renameNowBtn = document.getElementById('rename-now-btn');

  async function execute() {
    const p = dirInput?.value?.trim();
    if (!p) return;
    const files = getSelectedMp3Paths();
    if (!files.length) {
      toast('Select at least one MP3');
      return;
    }
    const r = await API.executeRename({ path: p, file_paths: files, dry_run: false });
    const op = r.operation_id;
    toast(`Started operation ${op}`);

    // poll
    for (let i = 0; i < 60; i++) {
      const st = await API.getOperation(op);
      if (st.status === 'completed') {
        toast(`Completed. renamed=${st.results?.renamed ?? 0}, skipped=${st.results?.skipped ?? 0}, errors=${st.results?.errors ?? 0}`);
        if (st.undo_session_id) {
          toast(`Undo available (10m): ${st.undo_session_id}`);
        }
        break;
      }
      if (st.status === 'failed' || st.status === 'cancelled') {
        toast(`Operation ${st.status}`);
        break;
      }
      await new Promise((r) => setTimeout(r, 500));
    }
  }

  if (floatingPreview) floatingPreview.addEventListener('click', () => preview().catch(e => toast(`Preview failed: ${e.message}`)));
  if (floatingRename) floatingRename.addEventListener('click', () => execute().catch(e => toast(`Execute failed: ${e.message}`)));
  if (renameNowBtn) renameNowBtn.addEventListener('click', () => execute().catch(e => toast(`Execute failed: ${e.message}`)));

  // Initial disabled state (will be enabled after directory load)
  updateActionButtons();
}

window.addEventListener('load', async () => {
  setApiBadge('loading', 'Connecting...');
  await refreshHealth();
  wire();

  // Try to load initial directory
  try {
    const init = await API._getJson('/api/directory/initial');
    if (init?.path) {
      await loadDirectory(init.path, false);
    }
  } catch (e) {
    // ignore
  }

  // Periodic health refresh
  setInterval(refreshHealth, 5000);
});
