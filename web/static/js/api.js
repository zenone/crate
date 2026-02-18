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

  async fileMetadata(path, write_metadata = false) {
    return this._postJson('/api/file/metadata', {
      path,
      recursive: false,
      write_metadata: !!write_metadata,
    });
  },

  albumArtUrl(path) {
    // GET /api/file/album-art?file_path=...
    const u = new URL('/api/file/album-art', window.location.origin);
    u.searchParams.set('file_path', path);
    return u.toString();
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

  async cancelOperation(operationId) {
    return this._postJson(`/api/operation/${encodeURIComponent(operationId)}/cancel`, null);
  },

  async getConfig() {
    return this._getJson('/api/config');
  },

  async getConfigDefaults() {
    return this._getJson('/api/config/defaults');
  },

  async resetConfig() {
    return this._postJson('/api/config/reset', null);
  },

  async updateConfig(updates) {
    return this._postJson('/api/config/update', { updates });
  },

  async depsStatus() {
    return this._getJson('/api/deps/status');
  },

  async installChromaprint() {
    return this._postJson('/api/deps/chromaprint/install', null);
  },

  async firstRunStatus() {
    return this._getJson('/api/config/first-run');
  },

  async completeFirstRun() {
    return this._postJson('/api/config/complete-first-run', null);
  },

  async validateTemplate(template) {
    return this._postJson('/api/template/validate', { template });
  },

  async analyzeContext(files) {
    return this._postJson('/api/analyze-context', { files });
  },

  // Phase 1: Volume Normalization
  async normalize({ path, mode = 'analyze', target_lufs = -11.5, recursive = true }) {
    return this._postJson('/api/normalize', {
      path,
      mode,
      target_lufs,
      recursive,
    });
  },

  // Phase 2: Cue Detection
  async detectCues({ path, detect_intro = true, detect_drops = true, detect_breakdowns = true, sensitivity = 0.5, max_cues = 8, recursive = true }) {
    return this._postJson('/api/detect-cues', {
      path,
      detect_intro,
      detect_drops,
      detect_breakdowns,
      sensitivity,
      max_cues,
      recursive,
    });
  },

  async exportCues(results, output_path) {
    return this._postJson('/api/export-cues', {
      results,
      output_path,
    });
  },

  // Phase 1.5: Peak Limiter
  async limit({ path, mode = 'analyze', ceiling_percent = 99.7, release_ms = 100.0, recursive = true }) {
    return this._postJson('/api/limit', {
      path,
      mode,
      ceiling_percent,
      release_ms,
      recursive,
    });
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
