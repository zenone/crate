/**
 * Main Application Logic for DJ MP3 Renamer
 * Initializes the app and handles user interactions
 */

class App {
    constructor() {
        this.api = new RenamerAPI();
        this.init();
    }

    /**
     * Initialize the application
     */
    async init() {
        console.log('DJ MP3 Renamer - Initializing...');

        // Check API health
        await this.checkAPIHealth();

        console.log('DJ MP3 Renamer - Ready!');
    }

    /**
     * Check API health and update UI
     */
    async checkAPIHealth() {
        const statusElement = document.getElementById('api-status');
        const versionElement = document.getElementById('api-version');

        try {
            const health = await this.api.health();

            // Update status
            statusElement.textContent = health.api === 'ready' ? 'Ready' : health.status;
            statusElement.className = 'status-value ready';

            // Update version
            versionElement.textContent = health.version;

            console.log('✓ API Health Check:', health);
        } catch (error) {
            // Update status with error
            statusElement.textContent = 'Error';
            statusElement.className = 'status-value error';
            versionElement.textContent = 'N/A';

            console.error('✗ API Health Check Failed:', error);
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
