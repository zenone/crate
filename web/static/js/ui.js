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

/**
 * Directory Browser Modal
 * Provides filesystem navigation for directory selection
 */
class DirectoryBrowser {
    constructor(api, ui) {
        this.api = api;
        this.ui = ui;
        this.currentPath = null;
        this.selectedPath = null;
        this.onSelect = null; // Callback when directory selected

        this.initElements();
        this.setupEventListeners();
    }

    /**
     * Initialize DOM elements
     */
    initElements() {
        this.modal = document.getElementById('directory-browser-modal');
        this.overlay = this.modal.querySelector('.modal-overlay');
        this.closeBtn = this.modal.querySelector('.modal-close');
        this.homeBtn = this.modal.querySelector('.breadcrumb-home');
        this.breadcrumbParts = document.getElementById('breadcrumb-parts');
        this.browserList = document.getElementById('browser-list');
        this.browserLoading = document.getElementById('browser-loading');
        this.browserEmpty = document.getElementById('browser-empty');
        this.pathDisplay = document.getElementById('browser-path-display');
        this.selectBtn = document.getElementById('browser-select-btn');
        this.cancelBtn = document.getElementById('browser-cancel-btn');
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Close modal
        this.closeBtn.addEventListener('click', () => this.close());
        this.cancelBtn.addEventListener('click', () => this.close());
        this.overlay.addEventListener('click', () => this.close());

        // Select directory
        this.selectBtn.addEventListener('click', () => this.selectCurrent());

        // Home button
        this.homeBtn.addEventListener('click', () => this.navigateToHome());

        // Keyboard shortcuts
        this.modal.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.close();
            if (e.key === 'Enter' && this.selectedPath) this.selectCurrent();
        });
    }

    /**
     * Open the directory browser
     */
    async open(startPath = null) {
        this.modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden'; // Prevent background scroll

        // Load initial directory
        await this.navigate(startPath);
    }

    /**
     * Close the directory browser
     */
    close() {
        this.modal.classList.add('hidden');
        document.body.style.overflow = '';
        this.selectedPath = null;
    }

    /**
     * Navigate to a directory
     */
    async navigate(path = null) {
        try {
            // Show loading
            this.ui.show(this.browserLoading);
            this.ui.hide(this.browserEmpty);
            this.browserList.innerHTML = '';

            // Fetch directory contents
            const result = await this.api.browseDirectory(path);

            this.currentPath = result.current_path;
            this.selectedPath = result.current_path; // Auto-select current directory
            this.pathDisplay.value = result.current_path;

            // Update breadcrumb
            this.updateBreadcrumb(result.path_parts, result.current_path);

            // Hide loading
            this.ui.hide(this.browserLoading);

            // Render directories
            if (result.directories.length === 0 && !result.parent_path) {
                this.ui.show(this.browserEmpty);
            } else {
                this.renderDirectories(result.directories, result.parent_path);
            }

        } catch (error) {
            this.ui.hide(this.browserLoading);
            this.ui.error(`Failed to browse directory: ${error.message}`);
            console.error('Directory browse error:', error);
        }
    }

    /**
     * Update breadcrumb navigation
     */
    updateBreadcrumb(parts, currentPath) {
        this.breadcrumbParts.innerHTML = '';

        parts.forEach((part, index) => {
            // Add separator
            if (index > 0) {
                const sep = document.createElement('span');
                sep.className = 'breadcrumb-separator';
                sep.textContent = '/';
                this.breadcrumbParts.appendChild(sep);
            }

            // Add part button
            const partBtn = document.createElement('button');
            partBtn.className = 'breadcrumb-part';
            partBtn.textContent = part;

            // Mark current part
            if (index === parts.length - 1) {
                partBtn.classList.add('current');
            } else {
                // Build path for this part
                const partPath = '/' + parts.slice(1, index + 1).join('/');
                partBtn.addEventListener('click', () => this.navigate(partPath));
            }

            this.breadcrumbParts.appendChild(partBtn);
        });
    }

    /**
     * Render directory list
     */
    renderDirectories(directories, parentPath) {
        this.browserList.innerHTML = '';

        // Add parent directory option if exists
        if (parentPath) {
            const parentItem = this.createDirectoryItem(
                '.. (parent directory)',
                parentPath,
                '⬆️',
                true
            );
            this.browserList.appendChild(parentItem);
        }

        // Add subdirectories
        directories.forEach(dir => {
            const item = this.createDirectoryItem(dir.name, dir.path, '📁', false);
            this.browserList.appendChild(item);
        });
    }

    /**
     * Create a directory item element
     */
    createDirectoryItem(name, path, icon, isParent = false) {
        const item = document.createElement('div');
        item.className = 'browser-item';
        if (isParent) item.classList.add('parent');
        item.dataset.path = path;

        const iconSpan = document.createElement('span');
        iconSpan.className = 'browser-item-icon';
        iconSpan.textContent = icon;

        const nameSpan = document.createElement('span');
        nameSpan.className = 'browser-item-name';
        nameSpan.textContent = name;

        item.appendChild(iconSpan);
        item.appendChild(nameSpan);

        // Single click to select
        item.addEventListener('click', () => {
            // Remove previous selection
            this.browserList.querySelectorAll('.browser-item').forEach(el => {
                el.classList.remove('selected');
            });

            // Select this item
            item.classList.add('selected');
            this.selectedPath = path;
            this.pathDisplay.value = path;
        });

        // Double click to navigate
        item.addEventListener('dblclick', () => {
            this.navigate(path);
        });

        return item;
    }

    /**
     * Navigate to home directory
     */
    async navigateToHome() {
        await this.navigate(null); // null = home directory
    }

    /**
     * Select current directory and close
     */
    selectCurrent() {
        if (this.selectedPath && this.onSelect) {
            this.onSelect(this.selectedPath);
        }
        this.close();
    }
}

// Export for use in app.js
window.UI = UI;
window.DirectoryBrowser = DirectoryBrowser;
