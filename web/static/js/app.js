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

async function loadDirectory(path, recursive = false) {
  const dirInput = document.getElementById('directory-path');
  if (dirInput) dirInput.value = path;
  const contents = await API.listDirectory(path, recursive);
  showFiles(contents);
}

function wire() {
  const browseBtn = document.getElementById('browse-btn');
  const refreshBtn = document.getElementById('refresh-btn');
  const dirInput = document.getElementById('directory-path');

  // Basic browse: open home listing and let user copy/paste path (minimal)
  if (browseBtn) {
    browseBtn.addEventListener('click', async () => {
      try {
        const r = await API.browseDirectory(dirInput?.value || null);
        toast(`Current: ${r.current_path}`);
        if (r.directories?.length) {
          toast(`Dirs: ${r.directories.slice(0, 5).map(d => d.name).join(', ')}${r.directories.length>5?'…':''}`);
        }
        // Minimal behavior: just set current_path
        if (dirInput) dirInput.value = r.current_path;
        await loadDirectory(r.current_path, true);
      } catch (e) {
        toast(`Browse failed: ${e.message}`);
      }
    });
  }

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

  // Wire preview + execute buttons if present
  const floatingPreview = document.getElementById('floating-preview-btn');
  const floatingRename = document.getElementById('floating-rename-btn');

  async function preview() {
    const p = dirInput?.value?.trim();
    if (!p) return;
    const files = getSelectedMp3Paths();
    const resp = await API.previewRename({ path: p, recursive: false, file_paths: files.length ? files : null });
    toast(`Preview: will_rename=${resp.stats?.will_rename ?? 0}, will_skip=${resp.stats?.will_skip ?? 0}, errors=${resp.stats?.errors ?? 0}`);
  }

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
    for (let i=0;i<60;i++) {
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
      await new Promise((r)=>setTimeout(r, 500));
    }
  }

  if (floatingPreview) floatingPreview.addEventListener('click', () => preview().catch(e=>toast(`Preview failed: ${e.message}`)));
  if (floatingRename) floatingRename.addEventListener('click', () => execute().catch(e=>toast(`Execute failed: ${e.message}`)));
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
