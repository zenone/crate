/**
 * Main Application Logic for DJ MP3 Renamer
 * Handles file browsing, metadata display, and user interactions
 */

class App {
    constructor() {
        this.api = new RenamerAPI();
        this.ui = new UI();
        this.directoryBrowser = null; // Will be initialized after DOM ready
        this.currentPath = '';
        this.currentFiles = [];
        this.selectedFiles = new Set();

        this.init();
    }

    /**
     * Initialize the application
     */
    async init() {
        console.log('DJ MP3 Renamer - Initializing...');

        // Initialize UI
        this.ui.init();

        // Initialize directory browser
        this.directoryBrowser = new DirectoryBrowser(this.api, this.ui);
        this.directoryBrowser.onSelect = (path) => this.onDirectorySelected(path);

        // Setup event listeners
        this.setupEventListeners();

        // Check API health
        await this.checkAPIHealth();

        // Set default path (user's home or desktop)
        this.setDefaultPath();

        console.log('DJ MP3 Renamer - Ready!');
    }

    /**
     * Setup all event listeners
     */
    setupEventListeners() {
        // Browse button - open directory browser modal
        document.getElementById('browse-btn').addEventListener('click', () => {
            this.openDirectoryBrowser();
        });

        // Directory input - Enter key
        document.getElementById('directory-path').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.loadDirectory();
            }
        });

        // Refresh button
        document.getElementById('refresh-btn').addEventListener('click', () => {
            if (this.currentPath) {
                this.loadDirectory();
            }
        });

        // Select all checkbox
        document.getElementById('select-all').addEventListener('change', (e) => {
            this.toggleSelectAll(e.target.checked);
        });

        // Preview button
        document.getElementById('preview-btn').addEventListener('click', () => {
            this.ui.toast('Preview functionality coming in Checkpoint 3!', 'info');
        });

        // Settings button
        document.getElementById('settings-btn').addEventListener('click', () => {
            this.ui.toast('Settings coming in Checkpoint 5!', 'info');
        });
    }

    /**
     * Check API health and update UI
     */
    async checkAPIHealth() {
        try {
            const health = await this.api.health();
            this.ui.updateStatusBadge('ready', '✓ Connected');
            console.log('✓ API Health Check:', health);
        } catch (error) {
            this.ui.updateStatusBadge('error', '✗ Connection Failed');
            this.ui.error('Failed to connect to API');
            console.error('✗ API Health Check Failed:', error);
        }
    }

    /**
     * Set default directory path
     */
    setDefaultPath() {
        // Try to use user's home directory or common music folder
        const homeDir = '~';
        const musicDir = '~/Music';

        document.getElementById('directory-path').value = musicDir;
        document.getElementById('directory-path').placeholder = musicDir;
    }

    /**
     * Open directory browser modal
     */
    async openDirectoryBrowser() {
        // Start with current path or home
        const currentPath = document.getElementById('directory-path').value.trim() || null;
        await this.directoryBrowser.open(currentPath);
    }

    /**
     * Handle directory selection from browser
     */
    onDirectorySelected(path) {
        // Fill the input with selected path
        document.getElementById('directory-path').value = path;

        // Automatically load the directory
        this.loadDirectory();
    }

    /**
     * Load directory contents
     */
    async loadDirectory() {
        const pathInput = document.getElementById('directory-path');
        const path = pathInput.value.trim();

        if (!path) {
            this.ui.warning('Please enter a directory path');
            return;
        }

        try {
            // Show loading state
            this.ui.show('file-list-section');
            this.ui.show('loading-files');
            this.ui.hide('no-files-message');
            document.getElementById('file-list-body').innerHTML = '';

            // Fetch directory contents
            const result = await this.api.listDirectory(path);

            // Update state
            this.currentPath = result.path;
            this.currentFiles = result.files.filter(f => f.is_mp3);
            this.selectedFiles.clear();

            // Update UI
            this.updateBreadcrumb(result.path);
            this.updateFileStats(result.total_files, result.mp3_count);

            // Hide loading, show files or empty state
            this.ui.hide('loading-files');

            if (this.currentFiles.length === 0) {
                this.ui.show('no-files-message');
            } else {
                await this.renderFileList();
                this.ui.show('actions-section');
            }

            this.ui.success(`Loaded ${result.mp3_count} MP3 file(s)`);

        } catch (error) {
            this.ui.hide('loading-files');
            this.ui.error(`Failed to load directory: ${error.message}`);
            console.error('Error loading directory:', error);
        }
    }

    /**
     * Update breadcrumb with current path
     */
    updateBreadcrumb(path) {
        const breadcrumb = document.getElementById('path-breadcrumb');
        breadcrumb.textContent = `📂 ${path}`;
        this.ui.show('path-breadcrumb');
    }

    /**
     * Update file statistics
     */
    updateFileStats(totalFiles, mp3Count) {
        document.getElementById('file-count').textContent = `${totalFiles} files`;
        document.getElementById('mp3-count').textContent = `${mp3Count} MP3s`;
    }

    /**
     * Render file list table
     */
    async renderFileList() {
        const tbody = document.getElementById('file-list-body');
        tbody.innerHTML = '';

        for (const file of this.currentFiles) {
            const row = await this.createFileRow(file);
            tbody.appendChild(row);
        }
    }

    /**
     * Create a table row for a file
     */
    async createFileRow(file) {
        const row = document.createElement('tr');
        row.dataset.path = file.path;

        // Checkbox
        const checkboxCell = document.createElement('td');
        checkboxCell.className = 'col-checkbox';
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.dataset.path = file.path;
        checkbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                this.selectedFiles.add(file.path);
            } else {
                this.selectedFiles.delete(file.path);
            }
            this.updatePreviewButton();
        });
        checkboxCell.appendChild(checkbox);
        row.appendChild(checkboxCell);

        // Filename
        const nameCell = document.createElement('td');
        nameCell.className = 'col-name';
        nameCell.textContent = file.name;
        nameCell.title = file.name;
        row.appendChild(nameCell);

        // Metadata cells (will load on demand)
        const artistCell = document.createElement('td');
        artistCell.className = 'col-artist';
        artistCell.textContent = '...';
        row.appendChild(artistCell);

        const titleCell = document.createElement('td');
        titleCell.className = 'col-title';
        titleCell.textContent = '...';
        row.appendChild(titleCell);

        const bpmCell = document.createElement('td');
        bpmCell.className = 'col-bpm';
        bpmCell.textContent = '...';
        row.appendChild(bpmCell);

        const keyCell = document.createElement('td');
        keyCell.className = 'col-key';
        keyCell.textContent = '...';
        row.appendChild(keyCell);

        // Actions
        const actionsCell = document.createElement('td');
        actionsCell.className = 'col-actions';
        const infoBtn = document.createElement('button');
        infoBtn.textContent = 'ℹ️ Info';
        infoBtn.className = 'btn btn-secondary';
        infoBtn.style.padding = '0.5rem 1rem';
        infoBtn.style.fontSize = '0.875rem';
        infoBtn.addEventListener('click', () => this.showFileInfo(file.path));
        actionsCell.appendChild(infoBtn);
        row.appendChild(actionsCell);

        // Load metadata in background
        this.loadFileMetadata(file.path, { artistCell, titleCell, bpmCell, keyCell });

        return row;
    }

    /**
     * Load metadata for a file
     */
    async loadFileMetadata(path, cells) {
        try {
            const result = await this.api.getFileMetadata(path);
            const meta = result.metadata;

            // Update cells
            cells.artistCell.textContent = meta.artist || '-';
            cells.titleCell.textContent = meta.title || '-';
            cells.bpmCell.textContent = meta.bpm || '-';
            cells.keyCell.textContent = meta.key || '-';

            // Add Camelot in parentheses if available
            if (meta.camelot) {
                cells.keyCell.textContent += ` (${meta.camelot})`;
            }

        } catch (error) {
            console.error(`Failed to load metadata for ${path}:`, error);
            cells.artistCell.textContent = '?';
            cells.titleCell.textContent = '?';
            cells.bpmCell.textContent = '?';
            cells.keyCell.textContent = '?';
        }
    }

    /**
     * Show detailed file information
     */
    async showFileInfo(path) {
        try {
            const result = await this.api.getFileMetadata(path);
            const meta = result.metadata;

            let info = `File: ${result.name}\n\n`;
            info += `Artist: ${meta.artist || '-'}\n`;
            info += `Title: ${meta.title || '-'}\n`;
            info += `Album: ${meta.album || '-'}\n`;
            info += `Year: ${meta.year || '-'}\n`;
            info += `BPM: ${meta.bpm || '-'}`;
            if (meta.bpm_source) info += ` (${meta.bpm_source})`;
            info += `\nKey: ${meta.key || '-'}`;
            if (meta.key_source) info += ` (${meta.key_source})`;
            if (meta.camelot) info += `\nCamelot: ${meta.camelot}`;

            alert(info);

        } catch (error) {
            this.ui.error(`Failed to load file info: ${error.message}`);
        }
    }

    /**
     * Toggle select all files
     */
    toggleSelectAll(checked) {
        const checkboxes = document.querySelectorAll('input[type="checkbox"][data-path]');
        checkboxes.forEach(cb => {
            cb.checked = checked;
            if (checked) {
                this.selectedFiles.add(cb.dataset.path);
            } else {
                this.selectedFiles.delete(cb.dataset.path);
            }
        });
        this.updatePreviewButton();
    }

    /**
     * Update preview button state
     */
    updatePreviewButton() {
        const previewBtn = document.getElementById('preview-btn');
        if (this.selectedFiles.size > 0 || this.currentFiles.length > 0) {
            previewBtn.disabled = false;
            previewBtn.textContent = `👁️ Preview Rename (${this.selectedFiles.size || this.currentFiles.length} files)`;
        } else {
            previewBtn.disabled = true;
            previewBtn.textContent = '👁️ Preview Rename';
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
