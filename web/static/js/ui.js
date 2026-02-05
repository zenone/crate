// Minimal UI wiring for Crate Web UI.

export function setApiBadge(state, text) {
  const badge = document.getElementById('api-status-badge');
  if (!badge) return;
  badge.classList.remove('loading', 'ok', 'error');
  badge.classList.add(state);
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
    tdArt.textContent = '';

    const tdName = document.createElement('td');
    tdName.className = 'col-current';
    tdName.textContent = f.name;

    const tdPreview = document.createElement('td');
    tdPreview.className = 'col-preview';
    tdPreview.textContent = '';

    const tdArtist = document.createElement('td');
    tdArtist.className = 'col-artist';
    tdArtist.textContent = '';

    const tdTitle = document.createElement('td');
    tdTitle.className = 'col-title';
    tdTitle.textContent = '';

    const tdAlbum = document.createElement('td');
    tdAlbum.className = 'col-album';
    tdAlbum.textContent = '';

    const tdYear = document.createElement('td');
    tdYear.className = 'col-year';
    tdYear.textContent = '';

    const tdGenre = document.createElement('td');
    tdGenre.className = 'col-genre';
    tdGenre.textContent = '';

    const tdDur = document.createElement('td');
    tdDur.className = 'col-duration';
    tdDur.textContent = '';

    const tdBpm = document.createElement('td');
    tdBpm.className = 'col-bpm';
    tdBpm.textContent = '';

    const tdKey = document.createElement('td');
    tdKey.className = 'col-key';
    tdKey.textContent = '';

    const tdSource = document.createElement('td');
    tdSource.className = 'col-source';
    tdSource.textContent = '';

    const tdActions = document.createElement('td');
    tdActions.className = 'col-actions';
    tdActions.textContent = '';

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
  }
}

export function getSelectedMp3Paths() {
  return Array.from(document.querySelectorAll('input.file-select:checked'))
    .map((el) => el.dataset.path)
    .filter(Boolean);
}
