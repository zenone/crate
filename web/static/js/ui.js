/**
 * UI Helper Functions for Crate
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
     * Show undo toast with countdown timer
     * @param {string} message - Success message
     * @param {function} undoCallback - Function to call when undo is clicked
     * @param {number} expiresInSeconds - Seconds until undo expires (default 30)
     */
    showUndoToast(message, undoCallback, expiresInSeconds = 30) {
        if (!this.toastContainer) {
            this.init();
        }

        const toast = document.createElement('div');
        toast.className = 'toast success toast-undo';
        toast.innerHTML = `
            <div class="toast-content">
                <div class="toast-message">${message}</div>
                <button class="toast-undo-btn">
                    ↶ Undo
                </button>
                <div class="toast-timer">
                    <span class="toast-timer-text">Undo available for <span class="toast-timer-seconds">${expiresInSeconds}</span>s</span>
                    <div class="toast-timer-bar">
                        <div class="toast-timer-fill"></div>
                    </div>
                </div>
            </div>
        `;

        // Get elements
        const undoBtn = toast.querySelector('.toast-undo-btn');
        const timerText = toast.querySelector('.toast-timer-seconds');
        const timerFill = toast.querySelector('.toast-timer-fill');

        // Undo button handler
        undoBtn.onclick = () => {
            undoCallback();
            toast.remove();
            clearInterval(timerInterval);
            clearTimeout(autoHideTimer);
        };

        // Add to DOM
        this.toastContainer.appendChild(toast);

        // Countdown timer
        let secondsRemaining = expiresInSeconds;

        const timerInterval = setInterval(() => {
            secondsRemaining--;
            timerText.textContent = secondsRemaining;

            const progress = (expiresInSeconds - secondsRemaining) / expiresInSeconds * 100;
            timerFill.style.width = `${progress}%`;

            if (secondsRemaining <= 0) {
                clearInterval(timerInterval);
            }
        }, 1000);

        // Auto-hide after expiry
        const autoHideTimer = setTimeout(() => {
            toast.classList.add('toast-fade-out');
            setTimeout(() => toast.remove(), 300);
        }, expiresInSeconds * 1000);

        return toast;
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
        this.sortMode = 'name-asc'; // Default sort mode
        this.currentDirectories = []; // Cache current directories for re-sorting
        this.currentFiles = []; // Cache current files for re-sorting
        this.currentParentPath = null;
        this.selectedFiles = new Set(); // Track selected file paths
        this.showFiles = true; // Show MP3 files with checkboxes

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
        this.sortSelect = document.getElementById('browser-sort-select');
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

        // Sort dropdown
        this.sortSelect.addEventListener('change', (e) => {
            this.sortMode = e.target.value;
            this.applySortAndRender();
        });

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

            // Clear file selection when navigating to new directory
            this.selectedFiles.clear();

            // Fetch directory contents (with files if showFiles is true)
            const result = await this.api.browseDirectory(path, this.showFiles);

            this.currentPath = result.current_path;
            this.selectedPath = result.current_path; // Auto-select current directory
            this.pathDisplay.value = result.current_path;

            // Update breadcrumb
            this.updateBreadcrumb(result.path_parts, result.current_path);

            // Hide loading
            this.ui.hide(this.browserLoading);

            // Render directories and files
            if (result.directories.length === 0 && result.files.length === 0 && !result.parent_path) {
                this.ui.show(this.browserEmpty);
            } else {
                this.renderDirectories(result.directories, result.files || [], result.parent_path);
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
     * Apply current sort and re-render
     */
    applySortAndRender() {
        const sortedDirs = this.sortDirectories(this.currentDirectories);
        const sortedFiles = this.sortFiles(this.currentFiles);
        this.renderDirectoriesInternal(sortedDirs, sortedFiles, this.currentParentPath);
    }

    /**
     * Sort directories based on current sort mode
     */
    sortDirectories(directories) {
        const sorted = [...directories]; // Create copy

        switch (this.sortMode) {
            case 'name-asc':
                sorted.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
                break;
            case 'name-desc':
                sorted.sort((a, b) => b.name.toLowerCase().localeCompare(a.name.toLowerCase()));
                break;
        }

        return sorted;
    }

    /**
     * Sort files based on current sort mode
     */
    sortFiles(files) {
        const sorted = [...files]; // Create copy

        switch (this.sortMode) {
            case 'name-asc':
                sorted.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
                break;
            case 'name-desc':
                sorted.sort((a, b) => b.name.toLowerCase().localeCompare(a.name.toLowerCase()));
                break;
        }

        return sorted;
    }

    /**
     * Render directory list
     */
    renderDirectories(directories, files, parentPath) {
        // Cache for sorting
        this.currentDirectories = directories;
        this.currentFiles = files;
        this.currentParentPath = parentPath;

        // Sort and render
        const sortedDirs = this.sortDirectories(directories);
        const sortedFiles = this.sortFiles(files);
        this.renderDirectoriesInternal(sortedDirs, sortedFiles, parentPath);
    }

    /**
     * Internal rendering method
     */
    renderDirectoriesInternal(directories, files, parentPath) {
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

        // Add MP3 files (if showFiles is enabled)
        if (this.showFiles && files.length > 0) {
            files.forEach(file => {
                const item = this.createFileItem(file.name, file.path, file.size);
                this.browserList.appendChild(item);
            });
        }

        // Update button text based on selection (should show "Select Folder" initially)
        this.updateSelectButtonText();
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

        // Single click to navigate into directory
        item.addEventListener('click', () => {
            this.navigate(path);
        });

        return item;
    }

    /**
     * Create a file item element with checkbox
     */
    createFileItem(name, path, size) {
        const item = document.createElement('div');
        item.className = 'browser-item file-item';
        item.dataset.path = path;

        // Checkbox
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'file-checkbox';
        checkbox.checked = this.selectedFiles.has(path);
        checkbox.addEventListener('change', (e) => {
            e.stopPropagation(); // Prevent item click
            if (checkbox.checked) {
                this.selectedFiles.add(path);
            } else {
                this.selectedFiles.delete(path);
            }
            this.updateSelectButtonText(); // Update button based on selection
        });

        // Icon
        const iconSpan = document.createElement('span');
        iconSpan.className = 'browser-item-icon';
        iconSpan.textContent = '🎵';

        // Name
        const nameSpan = document.createElement('span');
        nameSpan.className = 'browser-item-name';
        nameSpan.textContent = name;

        // Size
        const sizeSpan = document.createElement('span');
        sizeSpan.className = 'browser-item-size';
        sizeSpan.textContent = this.formatFileSize(size);

        item.appendChild(checkbox);
        item.appendChild(iconSpan);
        item.appendChild(nameSpan);
        item.appendChild(sizeSpan);

        // Click to toggle checkbox
        item.addEventListener('click', () => {
            checkbox.checked = !checkbox.checked;
            checkbox.dispatchEvent(new Event('change'));
        });

        return item;
    }

    /**
     * Format file size for display
     */
    formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    /**
     * Navigate to home directory
     */
    async navigateToHome() {
        await this.navigate(null); // null = home directory
    }

    /**
     * Update select button text based on file selection
     */
    updateSelectButtonText() {
        if (!this.selectBtn) return;

        const count = this.selectedFiles.size;

        if (count > 0) {
            this.selectBtn.textContent = `Select Files (${count})`;
            this.selectBtn.classList.add('has-selection');
        } else {
            this.selectBtn.textContent = 'Select Folder';
            this.selectBtn.classList.remove('has-selection');
        }
    }

    /**
     * Select current directory or selected files and close
     */
    selectCurrent() {
        if (this.selectedFiles.size > 0) {
            // User has selected specific files - return file paths
            const filePaths = Array.from(this.selectedFiles);
            if (this.onSelect) {
                this.onSelect(this.selectedPath, filePaths); // Pass both folder and files
            }
        } else {
            // No files selected - return folder path (load all files)
            if (this.selectedPath && this.onSelect) {
                this.onSelect(this.selectedPath, null); // null = all files
            }
        }
        this.close();
    }
}

// Export for use in app.js
window.UI = UI;
window.DirectoryBrowser = DirectoryBrowser;
