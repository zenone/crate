/**
 * API Client for DJ MP3 Renamer
 * Handles all communication with the FastAPI backend
 */

class RenamerAPI {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
    }

    /**
     * Generic fetch wrapper with error handling
     */
    async _fetch(endpoint, options = {}) {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    }

    /**
     * Health check
     * @returns {Promise<Object>} { status, version, api }
     */
    async health() {
        return this._fetch('/api/health');
    }

    /**
     * List directory contents
     * @param {string} path - Directory path
     * @returns {Promise<Object>} { path, files, total_files, mp3_count }
     */
    async listDirectory(path) {
        return this._fetch('/api/directory/list', {
            method: 'POST',
            body: JSON.stringify({ path })
        });
    }

    /**
     * Get metadata for a specific file
     * @param {string} path - File path
     * @returns {Promise<Object>} { path, name, metadata }
     */
    async getFileMetadata(path) {
        return this._fetch('/api/file/metadata', {
            method: 'POST',
            body: JSON.stringify({ path })
        });
    }

    /**
     * Validate a template
     * @param {string} template - Template string
     * @returns {Promise<Object>} { valid, errors, warnings, example }
     */
    async validateTemplate(template) {
        return this._fetch('/api/template/validate', {
            method: 'POST',
            body: JSON.stringify({ template })
        });
    }

    /**
     * Preview rename operation
     * @param {string} path - Directory path
     * @param {boolean} recursive - Include subdirectories
     * @param {string} template - Optional custom template
     * @returns {Promise<Object>} { path, previews, total }
     */
    async previewRename(path, recursive = false, template = null) {
        return this._fetch('/api/rename/preview', {
            method: 'POST',
            body: JSON.stringify({ path, recursive, template })
        });
    }

    /**
     * Get current configuration
     * @returns {Promise<Object>} Configuration object
     */
    async getConfig() {
        return this._fetch('/api/config');
    }

    /**
     * Update configuration
     * @param {Object} updates - Configuration updates
     * @returns {Promise<Object>} { success, message }
     */
    async updateConfig(updates) {
        return this._fetch('/api/config/update', {
            method: 'POST',
            body: JSON.stringify({ updates })
        });
    }

    // Future methods for Checkpoint 3+
    // - startRenameAsync(request)
    // - getOperationStatus(operationId)
    // - cancelOperation(operationId)
    // - analyzeFile(filePath)
}

// Export for use in app.js
window.RenamerAPI = RenamerAPI;
