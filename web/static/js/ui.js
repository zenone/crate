/**
 * UI Helper Functions for DJ MP3 Renamer
 * Provides toast notifications, loading states, and other UI utilities
 */

class UI {
    constructor() {
        this.toastContainer = null;
    }

    /**
     * Initialize UI components
     */
    init() {
        this.toastContainer = document.getElementById('toast-container');
    }

    /**
     * Show a toast notification
     * @param {string} message - Message to display
     * @param {string} type - Type: 'success', 'error', 'warning', 'info'
     * @param {number} duration - Duration in ms (0 = permanent)
     */
    toast(message, type = 'info', duration = 4000) {
        if (!this.toastContainer) {
            this.init();
        }

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const messageEl = document.createElement('div');
        messageEl.className = 'toast-message';
        messageEl.textContent = message;

        toast.appendChild(messageEl);
        this.toastContainer.appendChild(toast);

        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transform = 'translateX(100%)';
                setTimeout(() => toast.remove(), 300);
            }, duration);
        }

        return toast;
    }

    /**
     * Show success toast
     */
    success(message, duration) {
        return this.toast(message, 'success', duration);
    }

    /**
     * Show error toast
     */
    error(message, duration) {
        return this.toast(message, 'error', duration);
    }

    /**
     * Show warning toast
     */
    warning(message, duration) {
        return this.toast(message, 'warning', duration);
    }

    /**
     * Show/hide element
     */
    show(element) {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        if (element) {
            element.classList.remove('hidden');
        }
    }

    hide(element) {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        if (element) {
            element.classList.add('hidden');
        }
    }

    /**
     * Toggle element visibility
     */
    toggle(element) {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        if (element) {
            element.classList.toggle('hidden');
        }
    }

    /**
     * Show loading state
     */
    showLoading(element, message = 'Loading...') {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        if (element) {
            element.innerHTML = `
                <div class="loading-indicator">
                    <div class="spinner"></div>
                    <p>${message}</p>
                </div>
            `;
            this.show(element);
        }
    }

    /**
     * Format file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    /**
     * Truncate filename
     */
    truncateFilename(filename, maxLength = 40) {
        if (filename.length <= maxLength) return filename;

        const ext = filename.substring(filename.lastIndexOf('.'));
        const name = filename.substring(0, filename.lastIndexOf('.'));
        const keepLength = maxLength - ext.length - 3; // 3 for '...'

        return name.substring(0, keepLength) + '...' + ext;
    }

    /**
     * Update status badge
     */
    updateStatusBadge(status, message) {
        const badge = document.getElementById('api-status-badge');
        if (!badge) return;

        badge.className = `status-badge ${status}`;
        badge.textContent = message;
    }
}

// Export for use in app.js
window.UI = UI;
