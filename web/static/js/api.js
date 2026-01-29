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

    // TODO: Add more API methods in Checkpoint 2
    // - listDirectory(path)
    // - previewRename(request)
    // - startRenameAsync(request)
    // - getOperationStatus(operationId)
    // - cancelOperation(operationId)
    // - validateTemplate(template)
    // - analyzeFile(filePath)
    // - getConfig()
    // - updateConfig(updates)
}

// Export for use in app.js
window.RenamerAPI = RenamerAPI;
