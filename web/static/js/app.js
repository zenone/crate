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
            this.showPreview();
        });

        // Rename Now button
        document.getElementById('rename-now-btn').addEventListener('click', () => {
            this.showRenameConfirmation();
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
     * Load directory contents (recursive by default)
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

            // Fetch directory contents RECURSIVELY (includes subdirectories)
            const result = await this.api.listDirectory(path, true);

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
        breadcrumb.textContent = `📂 ${path} (including subdirectories)`;
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

        // Filename (show relative path for subdirectories)
        const nameCell = document.createElement('td');
        nameCell.className = 'col-name';

        // Show relative path if file is in subdirectory
        const filePath = file.path;
        const currentPath = this.currentPath;

        if (filePath.startsWith(currentPath)) {
            // Calculate relative path
            const relativePath = filePath.substring(currentPath.length);
            const cleanPath = relativePath.startsWith('/') ? relativePath.substring(1) : relativePath;

            // If in subdirectory, show subdirectory with file name
            if (cleanPath.includes('/')) {
                const parts = cleanPath.split('/');
                const subdir = parts.slice(0, -1).join('/');
                const filename = parts[parts.length - 1];

                // Show subdirectory in muted color + filename
                nameCell.innerHTML = `<span style="color: var(--text-secondary);">${subdir}/</span>${filename}`;
            } else {
                nameCell.textContent = cleanPath;
            }
        } else {
            nameCell.textContent = file.name;
        }

        nameCell.title = file.path;  // Full path on hover
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
     * Update preview and rename button states
     */
    updatePreviewButton() {
        const previewBtn = document.getElementById('preview-btn');
        const renameNowBtn = document.getElementById('rename-now-btn');
        const fileCount = this.selectedFiles.size || this.currentFiles.length;

        if (fileCount > 0) {
            previewBtn.disabled = false;
            previewBtn.textContent = `👁️ Preview Rename (${fileCount} files)`;

            renameNowBtn.disabled = false;
            renameNowBtn.textContent = `✅ Rename Now (${fileCount} files)`;
        } else {
            previewBtn.disabled = true;
            previewBtn.textContent = '👁️ Preview Rename';

            renameNowBtn.disabled = true;
            renameNowBtn.textContent = '✅ Rename Now';
        }
    }

    /**
     * Show preview modal
     */
    async showPreview() {
        if (!this.currentPath) {
            this.ui.warning('Please select a directory first');
            return;
        }

        try {
            // Show preview modal
            const modal = document.getElementById('preview-modal');
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';

            // Show loading
            this.ui.show('preview-loading');
            this.ui.hide('preview-list');
            this.ui.hide('preview-empty');

            // Get file paths to preview (selected or all)
            const filePaths = this.selectedFiles.size > 0
                ? Array.from(this.selectedFiles)
                : this.currentFiles.map(f => f.path);

            // Call preview API
            const result = await this.api.previewRename(this.currentPath, false, null, filePaths);

            // Hide loading
            this.ui.hide('preview-loading');

            // Update statistics
            document.getElementById('preview-stat-total').textContent = result.total;
            document.getElementById('preview-stat-rename').textContent = result.stats.will_rename;
            document.getElementById('preview-stat-skip').textContent = result.stats.will_skip;
            document.getElementById('preview-stat-errors').textContent = result.stats.errors;

            // Render preview items
            if (result.previews.length === 0) {
                this.ui.show('preview-empty');
            } else {
                this.renderPreviewList(result.previews);
                this.ui.show('preview-list');
            }

            // Setup modal event listeners
            this.setupPreviewModalListeners();

        } catch (error) {
            this.ui.error(`Failed to generate preview: ${error.message}`);
            console.error('Preview error:', error);
            this.closePreviewModal();
        }
    }

    /**
     * Render preview list
     */
    renderPreviewList(previews) {
        const container = document.getElementById('preview-list');
        container.innerHTML = '';

        previews.forEach(preview => {
            const item = this.createPreviewItem(preview);
            container.appendChild(item);
        });
    }

    /**
     * Create a preview item element
     */
    createPreviewItem(preview) {
        const item = document.createElement('div');
        item.className = `preview-item ${preview.status}`;
        item.dataset.path = preview.src;

        // Checkbox (only for items that will rename)
        const checkboxDiv = document.createElement('div');
        checkboxDiv.className = 'preview-checkbox';

        if (preview.status === 'will_rename') {
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.checked = true;
            checkbox.dataset.path = preview.src;
            checkbox.addEventListener('change', () => this.updatePreviewExecuteButton());
            checkboxDiv.appendChild(checkbox);
        }
        item.appendChild(checkboxDiv);

        // Info section
        const info = document.createElement('div');
        info.className = 'preview-info';

        // Original name
        const originalName = preview.src.split('/').pop();
        const originalDiv = document.createElement('div');
        originalDiv.className = 'preview-original';
        originalDiv.textContent = `Original: ${originalName}`;
        info.appendChild(originalDiv);

        // New name or reason
        if (preview.status === 'will_rename') {
            const newName = preview.dst.split('/').pop();
            const newDiv = document.createElement('div');
            newDiv.className = 'preview-new';
            newDiv.innerHTML = `<span class="preview-arrow">→</span> ${newName}`;
            info.appendChild(newDiv);

            // Metadata source badges
            if (preview.metadata) {
                const sourcesDiv = document.createElement('div');
                sourcesDiv.className = 'preview-metadata-sources';

                // Show unique metadata sources
                const sources = new Set();
                if (preview.metadata.artist_source) sources.add(preview.metadata.artist_source);
                if (preview.metadata.title_source) sources.add(preview.metadata.title_source);
                if (preview.metadata.bpm_source) sources.add(preview.metadata.bpm_source);
                if (preview.metadata.key_source) sources.add(preview.metadata.key_source);

                sources.forEach(source => {
                    const badge = document.createElement('span');
                    badge.className = 'metadata-badge';

                    if (source === 'Tags') {
                        badge.classList.add('source-tags');
                        badge.textContent = '🏷️ ID3 Tags';
                    } else if (source === 'MusicBrainz') {
                        badge.classList.add('source-musicbrainz');
                        badge.textContent = '🎵 MusicBrainz';
                    } else if (source === 'AI Audio') {
                        badge.classList.add('source-ai');
                        badge.textContent = '🤖 AI Analysis';
                    }

                    sourcesDiv.appendChild(badge);
                });

                if (sources.size > 0) {
                    info.appendChild(sourcesDiv);
                }
            }
        } else {
            const reasonDiv = document.createElement('div');
            reasonDiv.className = 'preview-reason';
            reasonDiv.textContent = preview.reason || 'Cannot rename';
            info.appendChild(reasonDiv);
        }

        item.appendChild(info);

        // Status icon
        const statusIcon = document.createElement('div');
        statusIcon.className = 'preview-status-icon';
        if (preview.status === 'will_rename') {
            statusIcon.textContent = '✅';
        } else if (preview.status === 'will_skip') {
            statusIcon.textContent = '⏭️';
        } else {
            statusIcon.textContent = '❌';
        }
        item.appendChild(statusIcon);

        return item;
    }

    /**
     * Setup preview modal event listeners
     */
    setupPreviewModalListeners() {
        // Close button
        const closeBtn = document.querySelector('#preview-modal .modal-close');
        closeBtn.onclick = () => this.closePreviewModal();

        // Cancel button
        const cancelBtn = document.getElementById('preview-cancel-btn');
        cancelBtn.onclick = () => this.closePreviewModal();

        // Overlay click
        const overlay = document.querySelector('#preview-modal .modal-overlay');
        overlay.onclick = () => this.closePreviewModal();

        // Select all checkbox
        const selectAllCheckbox = document.getElementById('preview-select-all');
        selectAllCheckbox.onchange = (e) => {
            const checkboxes = document.querySelectorAll('#preview-list input[type="checkbox"]');
            checkboxes.forEach(cb => cb.checked = e.target.checked);
            this.updatePreviewExecuteButton();
        };

        // Execute button
        const executeBtn = document.getElementById('preview-execute-btn');
        executeBtn.onclick = () => this.executeRename();

        // Keyboard shortcuts
        const modal = document.getElementById('preview-modal');
        modal.onkeydown = (e) => {
            if (e.key === 'Escape') this.closePreviewModal();
        };

        // Initial button state
        this.updatePreviewExecuteButton();
    }

    /**
     * Update execute button state
     */
    updatePreviewExecuteButton() {
        const executeBtn = document.getElementById('preview-execute-btn');
        const checkboxes = document.querySelectorAll('#preview-list input[type="checkbox"]:checked');
        const count = checkboxes.length;

        executeBtn.disabled = count === 0;
        executeBtn.textContent = count > 0
            ? `✅ Rename Selected Files (${count})`
            : '✅ Rename Selected Files';

        // Update selection count
        document.getElementById('preview-selection-count').textContent = `${count} selected`;
    }

    /**
     * Close preview modal
     */
    closePreviewModal() {
        const modal = document.getElementById('preview-modal');
        modal.classList.add('hidden');
        document.body.style.overflow = '';
    }

    /**
     * Execute rename operation
     */
    async executeRename() {
        // Get selected file paths
        const checkboxes = document.querySelectorAll('#preview-list input[type="checkbox"]:checked');
        const filePaths = Array.from(checkboxes).map(cb => cb.dataset.path);

        if (filePaths.length === 0) {
            this.ui.warning('No files selected');
            return;
        }

        // Close preview modal
        this.closePreviewModal();

        // Show progress overlay
        this.showProgressOverlay(filePaths.length);

        try {
            // Start rename operation
            const result = await this.api.executeRename(this.currentPath, filePaths);
            const operationId = result.operation_id;

            // Poll for progress
            await this.pollOperationProgress(operationId);

        } catch (error) {
            this.ui.error(`Failed to start rename operation: ${error.message}`);
            console.error('Execute error:', error);
            this.closeProgressOverlay();
        }
    }

    /**
     * Show progress overlay
     */
    showProgressOverlay(totalFiles) {
        const overlay = document.getElementById('progress-overlay');
        overlay.classList.remove('hidden');
        document.body.style.overflow = 'hidden';

        // Initialize progress
        document.getElementById('progress-percent').textContent = '0%';
        document.getElementById('progress-current').textContent = '0';
        document.getElementById('progress-total').textContent = totalFiles;
        document.getElementById('progress-bar').style.width = '0%';
        document.getElementById('progress-output').innerHTML = '';
        document.getElementById('progress-message').textContent = 'Starting rename operation...';

        // Show cancel button, hide done button
        document.getElementById('progress-cancel-btn').classList.remove('hidden');
        document.getElementById('progress-done-btn').classList.add('hidden');

        // Setup cancel button
        document.getElementById('progress-cancel-btn').onclick = () => this.cancelOperation();
    }

    /**
     * Poll operation progress
     */
    async pollOperationProgress(operationId) {
        const pollInterval = 500; // 500ms
        let cancelled = false;

        // Store operation ID for cancellation
        this.currentOperationId = operationId;

        while (!cancelled) {
            try {
                const status = await this.api.getOperationStatus(operationId);

                // Update progress
                const percent = status.total > 0
                    ? Math.round((status.progress / status.total) * 100)
                    : 0;

                document.getElementById('progress-percent').textContent = `${percent}%`;
                document.getElementById('progress-current').textContent = status.progress;
                document.getElementById('progress-bar').style.width = `${percent}%`;
                document.getElementById('progress-message').textContent =
                    status.current_file ? `Processing: ${status.current_file}` : '';

                // Check if operation is complete
                if (status.status === 'completed') {
                    this.onOperationComplete(status);
                    break;
                } else if (status.status === 'cancelled') {
                    this.onOperationCancelled();
                    break;
                } else if (status.status === 'error') {
                    this.onOperationError(status.error);
                    break;
                }

                // Wait before next poll
                await new Promise(resolve => setTimeout(resolve, pollInterval));

            } catch (error) {
                console.error('Error polling operation:', error);
                this.ui.error('Lost connection to operation');
                this.closeProgressOverlay();
                break;
            }
        }
    }

    /**
     * Cancel current operation
     */
    async cancelOperation() {
        if (!this.currentOperationId) return;

        try {
            await this.api.cancelOperation(this.currentOperationId);
            document.getElementById('progress-message').textContent = 'Cancelling...';
        } catch (error) {
            console.error('Error cancelling operation:', error);
        }
    }

    /**
     * Handle operation complete
     */
    onOperationComplete(status) {
        const results = status.results;

        // Update progress output
        const output = document.getElementById('progress-output');
        output.innerHTML = '';

        results.results.forEach(result => {
            const line = document.createElement('div');
            line.className = 'progress-output-line';

            if (result.status === 'renamed') {
                line.classList.add('success');
                const oldName = result.src.split('/').pop();
                const newName = result.dst.split('/').pop();
                line.textContent = `✓ ${oldName} → ${newName}`;
            } else if (result.status === 'skipped') {
                line.classList.add('skip');
                const name = result.src.split('/').pop();
                line.textContent = `⏭ ${name}: ${result.message}`;
            } else {
                line.classList.add('error');
                const name = result.src.split('/').pop();
                line.textContent = `✗ ${name}: ${result.message}`;
            }

            output.appendChild(line);
        });

        // Update message
        document.getElementById('progress-message').textContent =
            `✅ Complete! Renamed ${results.renamed} of ${results.total} files`;

        // Show done button, hide cancel
        document.getElementById('progress-cancel-btn').classList.add('hidden');
        const doneBtn = document.getElementById('progress-done-btn');
        doneBtn.classList.remove('hidden');
        doneBtn.onclick = () => {
            this.closeProgressOverlay();
            this.loadDirectory(); // Refresh file list
        };

        // Show success toast
        this.ui.success(`Successfully renamed ${results.renamed} files!`);
    }

    /**
     * Handle operation cancelled
     */
    onOperationCancelled() {
        document.getElementById('progress-message').textContent = '⚠️ Operation cancelled by user';

        // Show done button
        document.getElementById('progress-cancel-btn').classList.add('hidden');
        const doneBtn = document.getElementById('progress-done-btn');
        doneBtn.classList.remove('hidden');
        doneBtn.onclick = () => {
            this.closeProgressOverlay();
            this.loadDirectory();
        };

        this.ui.warning('Rename operation cancelled');
    }

    /**
     * Handle operation error
     */
    onOperationError(errorMessage) {
        document.getElementById('progress-message').textContent = `❌ Error: ${errorMessage}`;

        // Show done button
        document.getElementById('progress-cancel-btn').classList.add('hidden');
        const doneBtn = document.getElementById('progress-done-btn');
        doneBtn.classList.remove('hidden');
        doneBtn.onclick = () => this.closeProgressOverlay();

        this.ui.error(`Operation failed: ${errorMessage}`);
    }

    /**
     * Close progress overlay
     */
    closeProgressOverlay() {
        const overlay = document.getElementById('progress-overlay');
        overlay.classList.add('hidden');
        document.body.style.overflow = '';
        this.currentOperationId = null;
    }

    /**
     * Show rename confirmation dialog
     */
    showRenameConfirmation() {
        if (!this.currentPath) {
            this.ui.warning('Please select a directory first');
            return;
        }

        const fileCount = this.selectedFiles.size || this.currentFiles.length;

        if (fileCount === 0) {
            this.ui.warning('No files to rename');
            return;
        }

        // Show modal
        const modal = document.getElementById('rename-confirm-modal');
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';

        // Update file count
        document.getElementById('rename-file-count').textContent = fileCount;

        // Setup event listeners
        this.setupRenameConfirmListeners();
    }

    /**
     * Setup rename confirmation modal listeners
     */
    setupRenameConfirmListeners() {
        // Close button
        const closeBtn = document.querySelector('#rename-confirm-modal .modal-close');
        closeBtn.onclick = () => this.closeRenameConfirmation();

        // Cancel button
        const cancelBtn = document.getElementById('rename-confirm-cancel-btn');
        cancelBtn.onclick = () => this.closeRenameConfirmation();

        // Overlay click
        const overlay = document.querySelector('#rename-confirm-modal .modal-overlay');
        overlay.onclick = () => this.closeRenameConfirmation();

        // Preview button (change mind - show preview instead)
        const previewBtn = document.getElementById('rename-confirm-preview-btn');
        previewBtn.onclick = () => {
            this.closeRenameConfirmation();
            this.showPreview();
        };

        // Execute button
        const executeBtn = document.getElementById('rename-confirm-execute-btn');
        executeBtn.onclick = () => {
            this.closeRenameConfirmation();
            this.executeRenameNow();
        };

        // Keyboard shortcuts
        const modal = document.getElementById('rename-confirm-modal');
        modal.onkeydown = (e) => {
            if (e.key === 'Escape') this.closeRenameConfirmation();
        };
    }

    /**
     * Close rename confirmation modal
     */
    closeRenameConfirmation() {
        const modal = document.getElementById('rename-confirm-modal');
        modal.classList.add('hidden');
        document.body.style.overflow = '';
    }

    /**
     * Execute rename immediately (without preview)
     */
    async executeRenameNow() {
        // Get file paths (selected or all)
        const filePaths = this.selectedFiles.size > 0
            ? Array.from(this.selectedFiles)
            : this.currentFiles.map(f => f.path);

        if (filePaths.length === 0) {
            this.ui.warning('No files to rename');
            return;
        }

        // Show progress overlay
        this.showProgressOverlay(filePaths.length);

        try {
            // Start rename operation
            const result = await this.api.executeRename(this.currentPath, filePaths);
            const operationId = result.operation_id;

            // Poll for progress
            await this.pollOperationProgress(operationId);

        } catch (error) {
            this.ui.error(`Failed to start rename operation: ${error.message}`);
            console.error('Execute error:', error);
            this.closeProgressOverlay();
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
