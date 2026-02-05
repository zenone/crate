// Minimal API client for Crate Web UI
// Intentionally no build step; plain browser JS.

export const API = {
  async health() {
    return this._getJson('/api/health');
  },

  async browseDirectory(path) {
    return this._postJson('/api/directory/browse', {
      path: path ?? null,
      include_parent: true,
      include_files: false,
    });
  },

  async listDirectory(path, recursive = false) {
    return this._postJson('/api/directory/list', {
      path,
      recursive,
      write_metadata: false,
    });
  },

  async previewRename({ path, recursive, template = null, enhance_metadata = false, file_paths = null }) {
    return this._postJson('/api/rename/preview', {
      path,
      recursive: !!recursive,
      template,
      enhance_metadata: !!enhance_metadata,
      file_paths,
    });
  },

  async executeRename({ path, dry_run = false, template = null, file_paths }) {
    // State-changing: include Origin header automatically (browser already does);
    // server enforces localhost origins.
    return this._postJson('/api/rename/execute', {
      path,
      dry_run: !!dry_run,
      template,
      file_paths,
    });
  },

  async getOperation(operationId) {
    return this._getJson(`/api/operation/${encodeURIComponent(operationId)}`);
  },

  async undoRename(sessionId) {
    // Server expects session_id as query param
    return this._postJson(`/api/rename/undo?session_id=${encodeURIComponent(sessionId)}`, null);
  },

  async _getJson(path) {
    const r = await fetch(path, { method: 'GET', headers: { 'Accept': 'application/json' } });
    if (!r.ok) throw new Error(`HTTP ${r.status} ${r.statusText}`);
    return await r.json();
  },

  async _postJson(path, obj) {
    const init = {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
      },
    };
    if (obj !== null) {
      init.headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(obj);
    }
    const r = await fetch(path, init);
    if (!r.ok) {
      const text = await r.text().catch(() => '');
      throw new Error(`HTTP ${r.status} ${r.statusText}${text ? `: ${text}` : ''}`);
    }
    return await r.json();
  },
};
