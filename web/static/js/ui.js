// Minimal UI wiring for Crate Web UI.

export function setApiBadge(state, text) {
  const badge = document.getElementById('api-status-badge');
  if (!badge) return;

  // Normalize state names to CSS classes
  // CSS supports: loading | ready | error
  const cssState = (state === 'ok') ? 'ready' : state;

  badge.classList.remove('loading', 'ready', 'error', 'ok');
  badge.classList.add(cssState);
  badge.textContent = text;
}

export function toast(msg) {
  // Minimal: console + optional toast container
  console.log(msg);
  const c = document.getElementById('toast-container');
  if (!c) return;
  const el = document.createElement('div');
  el.className = 'toast';
  el.textContent = msg;
  c.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

export function showFiles(contents) {
  const section = document.getElementById('file-list-section');
  const tbody = document.getElementById('file-list-body');
  const fileCount = document.getElementById('file-count');
  const mp3Count = document.getElementById('mp3-count');

  if (!section || !tbody) return;

  section.classList.remove('hidden');

  const files = contents.files || [];
  if (fileCount) fileCount.textContent = `${contents.total_files ?? files.length} files`;
  if (mp3Count) mp3Count.textContent = `${contents.mp3_count ?? 0} MP3s`;

  tbody.innerHTML = '';

  for (const f of files) {
    const tr = document.createElement('tr');
    tr.dataset.path = f.path;

    const tdCheck = document.createElement('td');
    tdCheck.className = 'col-checkbox';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.className = 'file-select';
    cb.dataset.path = f.path;
    cb.disabled = !f.is_mp3;
    tdCheck.appendChild(cb);

    const tdArt = document.createElement('td');
    tdArt.className = 'col-artwork';

    const tdName = document.createElement('td');
    tdName.className = 'col-current';
    tdName.textContent = f.name;

    const tdPreview = document.createElement('td');
    tdPreview.className = 'col-preview';
    tdPreview.textContent = '';

    const tdArtist = document.createElement('td');
    tdArtist.className = 'col-artist';

    const tdTitle = document.createElement('td');
    tdTitle.className = 'col-title';

    const tdAlbum = document.createElement('td');
    tdAlbum.className = 'col-album';

    const tdYear = document.createElement('td');
    tdYear.className = 'col-year';

    const tdGenre = document.createElement('td');
    tdGenre.className = 'col-genre';

    const tdDur = document.createElement('td');
    tdDur.className = 'col-duration';

    const tdBpm = document.createElement('td');
    tdBpm.className = 'col-bpm';

    const tdKey = document.createElement('td');
    tdKey.className = 'col-key';

    const tdSource = document.createElement('td');
    tdSource.className = 'col-source';

    const tdActions = document.createElement('td');
    tdActions.className = 'col-actions';

    tr.appendChild(tdCheck);
    tr.appendChild(tdArt);
    tr.appendChild(tdName);
    tr.appendChild(tdPreview);
    tr.appendChild(tdArtist);
    tr.appendChild(tdTitle);
    tr.appendChild(tdAlbum);
    tr.appendChild(tdYear);
    tr.appendChild(tdGenre);
    tr.appendChild(tdDur);
    tr.appendChild(tdBpm);
    tr.appendChild(tdKey);
    tr.appendChild(tdSource);
    tr.appendChild(tdActions);

    tbody.appendChild(tr);

    // Fill metadata if already present
    if (f.metadata) {
      // Default mode here; app.js will re-apply with the user's setting after config load.
      updateRowMetadata(f.path, f.metadata, null, { keyDisplayMode: 'musical' });
    }
  }
}

export function updateRowMetadata(path, metadata, albumArtUrl = null, opts = null) {
  const row = document.querySelector(`tr[data-path="${cssEscape(path)}"]`);
  if (!row) return;

  const getTd = (cls) => row.querySelector(`td.${cls}`);

  const setText = (cls, v) => {
    const td = getTd(cls);
    if (!td) return;
    td.textContent = v ?? '';
  };

  setText('col-artist', metadata.artist);
  setText('col-title', metadata.title);
  setText('col-album', metadata.album);
  setText('col-year', metadata.year);
  setText('col-genre', metadata.genre);
  setText('col-bpm', metadata.bpm);

  const mode = (opts && opts.keyDisplayMode) ? String(opts.keyDisplayMode) : 'musical';
  const musical = metadata.key || '';
  const camelot = metadata.camelot || '';
  let keyText = '';
  if (mode === 'camelot') keyText = camelot || musical;
  else if (mode === 'both') {
    if (camelot && musical) keyText = `${camelot} (${musical})`;
    else keyText = camelot || musical;
  } else {
    keyText = musical || camelot;
  }
  setText('col-key', keyText);

  // Duration may be seconds or mm:ss; just display if present
  setText('col-duration', metadata.duration || metadata.length || '');

  // Source badges (basic)
  const srcTd = getTd('col-source');
  if (srcTd) {
    srcTd.textContent = metadata.source || '';
  }

  // Album art
  if (albumArtUrl) {
    const artTd = getTd('col-artwork');
    if (artTd && artTd.childElementCount === 0) {
      const img = document.createElement('img');
      img.src = albumArtUrl;
      img.alt = 'Album art';
      img.loading = 'lazy';
      img.style.width = '32px';
      img.style.height = '32px';
      img.style.borderRadius = '6px';
      img.style.objectFit = 'cover';
      img.addEventListener('error', () => {
        // Ignore missing art
        img.remove();
      });
      artTd.appendChild(img);
    }
  }
}

function cssEscape(s) {
  // minimal CSS.escape polyfill for file paths
  return String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

export function getSelectedMp3Paths() {
  return Array.from(document.querySelectorAll('input.file-select:checked'))
    .map((el) => el.dataset.path)
    .filter(Boolean);
}
