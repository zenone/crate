/**
 * Main Application Logic for Crate
 * Handles file browsing, metadata display, and user interactions
 */

console.log('Loading app.js - Version 20260131-21 - FEATURE: Per-album smart detection (Task #111)');

class App {
    constructor() {
        this.api = new RenamerAPI();
        this.ui = new UI();
        this.directoryBrowser = null; // Will be initialized after DOM ready
        this.currentPath = '';
        this.currentFiles = [];
        this.selectedFiles = new Set();
        this.lastRenameSessionId = null; // For undo functionality

        // Metadata loading progress tracking
        this.metadataLoadState = {
            total: 0,
            loaded: 0,
            startTime: null,
            estimatedTimeRemaining: null,
            currentFile: null
        };

        // Template validation debounce timer
        this.templateValidationTimeout = null;

        // Table sorting state
        this.sortState = {
            column: 'name',  // Default sort by filename
            direction: 'asc' // ascending
        };

        // Search/filter state
        this.searchQuery = '';
        this.searchTimeout = null;
        this.filteredFiles = [];

        // Temporary template from Smart Track Detection (Task #94)
        // This is used when "Use This" is clicked - it does NOT save to settings
        // Cleared when loading a new directory
        this.temporaryTemplate = null;

        // Smart banner dismissal state (Task #105)
        // Dismissed only for current directory load (not persistent across refreshes)
        // Resets when page refreshes or when loading different directory
        this.smartBannerDismissedForCurrentLoad = false;

        // Preview loading cancellation (Task #89)
        this.previewAbortController = null;

        // Metadata loading cancellation (Task #126)
        this.metadataAbortController = null;

        // Task #111: Per-album smart detection state
        this.perAlbumState = {
            enabled: false,           // Feature flag state
            directory: null,          // Current directory (for validation)
            albums: [],               // Album detection results
            locked: false,            // Locked during operations (prevent changes)
            timestamp: null           // When state was created (for staleness check)
        };
        this.perAlbumTemplates = null;  // Per-album template selections for preview/rename

        // Task #121: Connection monitoring
        this.connectionCheckInterval = null;  // Interval ID for health checks
        this.isConnected = false;             // Connection state

        this.init();
    }

    /**
     * Initialize the application
     */
    async init() {
        console.log('Crate - Initializing...');

        // Initialize UI
        this.ui.init();

        // Initialize directory browser
        this.directoryBrowser = new DirectoryBrowser(this.api, this.ui);
        this.directoryBrowser.onSelect = (path, filePaths) => this.onDirectorySelected(path, filePaths);

        // Setup event listeners
        this.setupEventListeners();

        // Setup keyboard shortcuts
        this.setupKeyboardShortcuts();

        // Setup search/filter
        this.setupSearchFilter();

        // Task #121: Check API health and start monitoring
        await this.checkAPIHealth();
        this.startConnectionMonitoring();

        // Check for first run and show welcome dialog if needed
        await this.checkFirstRun();

        // Task #84: Remember Last Directory - Option 2 (Set Path Only, Don't Auto-Load)
        // Sets the path in input field but doesn't load files
        // User presses Enter or clicks Browse to load
        try {
            const initialDir = await this.api.getInitialDirectory();

            if (initialDir.path) {
                // Set path in input field
                document.getElementById('directory-path').value = initialDir.path;

                // Log based on source
                if (initialDir.source === 'remembered') {
                    console.log(`[Task #84] Restored last directory path: ${initialDir.path}`);
                    console.log('[Task #84] Press Enter or click Browse to load files');
                } else if (initialDir.source === 'fallback') {
                    console.log(`[Task #84] Fallback - Directory deleted, using parent: ${initialDir.path}`);
                    this.ui.warning('Previous directory no longer exists. Restored parent path. Press Enter to load.');
                } else if (initialDir.source === 'home') {
                    console.log(`[Task #84] Using home directory (no saved path): ${initialDir.path}`);
                }

                // DON'T auto-load - let user explicitly trigger load by pressing Enter or clicking Browse
                // This avoids wasted computation and gives user full control
            } else {
                // No initial directory available, use default
                this.setDefaultPath();
            }
        } catch (error) {
            console.error('[Task #84] Error loading initial directory:', error);
            // Graceful degradation: Fall back to default path
            this.setDefaultPath();
            // Don't show error to user - feature failure is non-critical
        }

        console.log('Crate - Ready!');
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

        // Preview Cancel button (Task #89)
        document.getElementById('preview-cancel-btn').addEventListener('click', () => {
            this.cancelPreviewLoading();
        });

        // Metadata/Preview Cancel button (Tasks #126, #127)
        const metadataCancelBtn = document.getElementById('metadata-cancel-btn');
        if (metadataCancelBtn) {
            metadataCancelBtn.addEventListener('click', () => {
                this.cancelMetadataLoading();
            });
        }

        // Rename Now button
        document.getElementById('rename-now-btn').addEventListener('click', () => {
            this.showRenameConfirmation();
        });

        // Floating action bar buttons
        document.getElementById('floating-preview-btn').addEventListener('click', () => {
            this.showPreview();
        });

        document.getElementById('floating-rename-btn').addEventListener('click', () => {
            this.showRenameConfirmation();
        });

        // Settings button (header)
        document.getElementById('settings-btn').addEventListener('click', () => {
            this.showSettings();
        });

        // Settings button (bottom - in actions section)
        document.getElementById('settings-btn-bottom').addEventListener('click', () => {
            this.showSettings();
        });

        // Sort dropdown
        document.getElementById('file-sort-select').addEventListener('change', (e) => {
            const [column, direction] = e.target.value.split('-');
            this.sortState.column = column;
            this.sortState.direction = direction;
            this.sortAndRenderFiles();
        });

        // Empty state CTA buttons
        document.getElementById('empty-browse-again-btn').addEventListener('click', () => {
            this.openDirectoryBrowser();
        });

        document.getElementById('preview-empty-close-btn').addEventListener('click', () => {
            this.closePreviewModal();
        });

        // Column header sorting (will be attached after table renders)
        this.setupColumnSorting();
    }

    /**
     * Setup column header sorting
     */
    setupColumnSorting() {
        // Use event delegation on the table
        const fileTable = document.getElementById('file-list');
        if (!fileTable) return;

        // Click handling
        fileTable.addEventListener('click', (e) => {
            const th = e.target.closest('th.sortable');
            if (!th) return;

            const column = th.dataset.sort;
            this.toggleSort(column);
        });

        // Keyboard handling for sortable headers
        fileTable.addEventListener('keydown', (e) => {
            const th = e.target.closest('th.sortable');
            if (!th) return;

            // Activate on Enter or Space
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                const column = th.dataset.sort;
                this.toggleSort(column);
            }
        });
    }

    /**
     * Setup keyboard shortcuts for power users
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Check for Cmd (Mac) or Ctrl (Windows/Linux)
            const modifier = e.metaKey || e.ctrlKey;

            // Ignore shortcuts if user is typing in an input/textarea
            const isTyping = e.target.tagName === 'INPUT' ||
                           e.target.tagName === 'TEXTAREA' ||
                           e.target.isContentEditable;

            // ? - Show shortcuts help (not while typing)
            if (e.key === '?' && !isTyping) {
                e.preventDefault();
                this.showShortcutsHelp();
                return;
            }

            // Escape - Close modals or blur input
            if (e.key === 'Escape') {
                if (isTyping) {
                    e.target.blur();
                }
                // Modal close is handled by individual modal listeners
                return;
            }

            // Don't process other shortcuts while typing
            if (isTyping) return;

            // Ctrl/Cmd+A - Select all files
            if (modifier && e.key === 'a') {
                e.preventDefault();
                if (this.currentFiles.length > 0) {
                    this.toggleSelectAll(true);
                }
                return;
            }

            // Ctrl/Cmd+D - Deselect all files
            if (modifier && e.key === 'd') {
                e.preventDefault();
                if (this.currentFiles.length > 0) {
                    this.toggleSelectAll(false);
                }
                return;
            }

            // Ctrl/Cmd+P - Preview rename
            if (modifier && e.key === 'p') {
                e.preventDefault();
                if (this.selectedFiles.size > 0) {
                    this.showPreview();
                }
                return;
            }

            // Ctrl/Cmd+Z - Undo last rename
            if (modifier && e.key === 'z') {
                e.preventDefault();
                if (this.lastRenameSessionId) {
                    this.undoRename(this.lastRenameSessionId);
                }
                return;
            }

            // Ctrl/Cmd+Enter - Execute rename (only in preview context)
            if (modifier && e.key === 'Enter') {
                // Check if preview modal is open
                const previewModal = document.getElementById('preview-modal');
                if (previewModal && !previewModal.classList.contains('hidden')) {
                    e.preventDefault();
                    const executeBtn = document.getElementById('preview-execute-btn');
                    if (executeBtn && !executeBtn.disabled) {
                        executeBtn.click();
                    }
                }
                return;
            }
        });
    }

    /**
     * Setup search/filter functionality for file list
     */
    setupSearchFilter() {
        const searchInput = document.getElementById('file-search-input');
        const clearBtn = document.getElementById('search-clear-btn');

        if (!searchInput || !clearBtn) return;

        // Handle search input with debounce
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();

            // Show/hide clear button
            if (query) {
                clearBtn.classList.remove('hidden');
            } else {
                clearBtn.classList.add('hidden');
            }

            // Debounce search (300ms)
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.searchQuery = query.toLowerCase();
                this.filterFiles();
            }, 300);
        });

        // Clear button handler
        clearBtn.addEventListener('click', () => {
            searchInput.value = '';
            clearBtn.classList.add('hidden');
            this.searchQuery = '';
            this.filterFiles();
            searchInput.focus();
        });

        // Keyboard shortcut: Ctrl+F to focus search
        document.addEventListener('keydown', (e) => {
            const modifier = e.metaKey || e.ctrlKey;
            const isTyping = e.target.tagName === 'INPUT' ||
                           e.target.tagName === 'TEXTAREA' ||
                           e.target.isContentEditable;

            // Ctrl/Cmd+F - Focus search (if files are loaded)
            if (modifier && e.key === 'f' && !isTyping) {
                if (this.currentFiles.length > 0) {
                    e.preventDefault();
                    searchInput.focus();
                }
            }

            // Escape - Clear search if search is focused
            if (e.key === 'Escape' && document.activeElement === searchInput) {
                if (searchInput.value) {
                    e.preventDefault();
                    searchInput.value = '';
                    clearBtn.classList.add('hidden');
                    this.searchQuery = '';
                    this.filterFiles();
                }
            }
        });
    }

    /**
     * Filter files based on search query
     */
    filterFiles() {
        const tbody = document.getElementById('file-list-body');
        const filteredCountEl = document.getElementById('filtered-count');

        if (!tbody || !filteredCountEl) return;

        // If no search query, show all rows
        if (!this.searchQuery) {
            const rows = tbody.querySelectorAll('tr');
            rows.forEach(row => row.classList.remove('hidden'));
            filteredCountEl.classList.add('hidden');
            this.filteredFiles = [...this.currentFiles];
            return;
        }

        // Filter files
        let visibleCount = 0;
        const rows = tbody.querySelectorAll('tr');

        rows.forEach(row => {
            const filePath = row.dataset.path;
            const file = this.currentFiles.find(f => f.path === filePath);

            if (!file) {
                row.classList.add('hidden');
                return;
            }

            // Search in: filename, artist, title
            const filename = file.name.toLowerCase();
            const artist = (file.metadata?.artist || '').toLowerCase();
            const title = (file.metadata?.title || '').toLowerCase();

            const matches = filename.includes(this.searchQuery) ||
                          artist.includes(this.searchQuery) ||
                          title.includes(this.searchQuery);

            if (matches) {
                row.classList.remove('hidden');
                visibleCount++;
            } else {
                row.classList.add('hidden');
            }
        });

        // Update filtered files array
        this.filteredFiles = this.currentFiles.filter(file => {
            const filename = file.name.toLowerCase();
            const artist = (file.metadata?.artist || '').toLowerCase();
            const title = (file.metadata?.title || '').toLowerCase();
            return filename.includes(this.searchQuery) ||
                   artist.includes(this.searchQuery) ||
                   title.includes(this.searchQuery);
        });

        // Show filtered count badge
        if (visibleCount < this.currentFiles.length) {
            filteredCountEl.textContent = `${visibleCount} shown`;
            filteredCountEl.classList.remove('hidden');
        } else {
            filteredCountEl.classList.add('hidden');
        }
    }

    /**
     * Toggle sort direction or change sort column
     */
    toggleSort(column) {
        if (this.sortState.column === column) {
            // Same column - toggle direction
            this.sortState.direction = this.sortState.direction === 'asc' ? 'desc' : 'asc';
        } else {
            // New column - default to ascending
            this.sortState.column = column;
            this.sortState.direction = 'asc';
        }

        this.applySortAndRender();
    }

    /**
     * Sort files and re-render table
     */
    applySortAndRender() {
        // Sort the current files array
        this.currentFiles.sort((a, b) => {
            return this.compareFiles(a, b, this.sortState.column, this.sortState.direction);
        });

        // Re-render the table
        this.renderFileList();

        // Update visual indicators
        this.updateSortIndicators();
    }

    /**
     * Compare two files for sorting
     */
    compareFiles(a, b, column, direction) {
        let aVal, bVal;

        // Get values based on column
        switch (column) {
            case 'name':
                aVal = a.name.toLowerCase();
                bVal = b.name.toLowerCase();
                break;
            case 'artist':
                // Metadata might not be loaded yet, use placeholder
                aVal = (a.metadata?.artist || '').toLowerCase();
                bVal = (b.metadata?.artist || '').toLowerCase();
                break;
            case 'title':
                aVal = (a.metadata?.title || '').toLowerCase();
                bVal = (b.metadata?.title || '').toLowerCase();
                break;
            case 'bpm':
                // Parse BPM as number
                aVal = parseInt(a.metadata?.bpm) || 0;
                bVal = parseInt(b.metadata?.bpm) || 0;
                break;
            case 'key':
                aVal = (a.metadata?.key || '').toLowerCase();
                bVal = (b.metadata?.key || '').toLowerCase();
                break;
            default:
                aVal = a.name.toLowerCase();
                bVal = b.name.toLowerCase();
        }

        // Compare values
        let result;
        if (typeof aVal === 'number') {
            result = aVal - bVal;
        } else {
            result = aVal.localeCompare(bVal);
        }

        // Apply direction
        return direction === 'asc' ? result : -result;
    }

    /**
     * Update visual sort indicators in table headers
     */
    updateSortIndicators() {
        // Remove active class from all headers and reset aria-sort
        document.querySelectorAll('th.sortable').forEach(th => {
            th.classList.remove('active');
            th.setAttribute('aria-sort', 'none');
            const indicator = th.querySelector('.sort-indicator');
            if (indicator) {
                indicator.className = 'sort-indicator';
            }
        });

        // Add active class and indicator to current sort column
        const activeHeader = document.querySelector(`th.sortable[data-sort="${this.sortState.column}"]`);
        if (activeHeader) {
            activeHeader.classList.add('active');
            // Set aria-sort based on direction
            activeHeader.setAttribute('aria-sort', this.sortState.direction === 'asc' ? 'ascending' : 'descending');
            const indicator = activeHeader.querySelector('.sort-indicator');
            if (indicator) {
                indicator.classList.add(this.sortState.direction);
            }
        }
    }

    /**
     * Enhance error message with actionable suggestions
     * @param {string} baseMessage - The base error message
     * @param {Error} error - The error object
     * @returns {string} Enhanced error message with suggestions
     */
    enhanceErrorMessage(baseMessage, error) {
        const errorMsg = error.message.toLowerCase();
        let suggestion = '';

        // Permission errors
        if (errorMsg.includes('permission') || errorMsg.includes('forbidden') || errorMsg.includes('403')) {
            suggestion = '\n\n💡 Check folder permissions or try running as administrator.';
        }
        // Not found errors
        else if (errorMsg.includes('not found') || errorMsg.includes('404')) {
            suggestion = '\n\n💡 The directory or file may have been moved or deleted.';
        }
        // Network/connection errors
        else if (errorMsg.includes('network') || errorMsg.includes('fetch') || errorMsg.includes('connection')) {
            suggestion = '\n\n💡 Check your internet connection or ensure the server is running.';
        }
        // Timeout errors
        else if (errorMsg.includes('timeout') || errorMsg.includes('timed out')) {
            suggestion = '\n\n💡 The operation took too long. Try with fewer files or check server performance.';
        }
        // Read-only/write errors
        else if (errorMsg.includes('read-only') || errorMsg.includes('cannot write')) {
            suggestion = '\n\n💡 The file or folder may be read-only. Check file properties.';
        }
        // File in use errors
        else if (errorMsg.includes('in use') || errorMsg.includes('locked') || errorMsg.includes('being used')) {
            suggestion = '\n\n💡 Close any programs that might be using these files.';
        }
        // Disk space errors
        else if (errorMsg.includes('disk') || errorMsg.includes('space') || errorMsg.includes('full')) {
            suggestion = '\n\n💡 Free up disk space and try again.';
        }
        // Invalid path errors
        else if (errorMsg.includes('invalid path') || errorMsg.includes('invalid directory')) {
            suggestion = '\n\n💡 Check that the path exists and is correctly formatted.';
        }
        // Template errors
        else if (errorMsg.includes('template') || errorMsg.includes('token')) {
            suggestion = '\n\n💡 Check your template syntax. Use valid tokens like {artist}, {title}, etc.';
        }
        // Metadata errors
        else if (errorMsg.includes('metadata') || errorMsg.includes('id3')) {
            suggestion = '\n\n💡 The file may be corrupted or have invalid metadata. Try another file.';
        }

        return baseMessage + suggestion;
    }

    /**
     * Check API health and update UI
     */
    async checkAPIHealth() {
        try {
            const health = await this.api.health();

            // Update connection state
            if (!this.isConnected) {
                this.isConnected = true;
                console.log('✓ API Connected');
            }

            this.ui.updateStatusBadge('ready', '✓ Connected');
        } catch (error) {
            // Update connection state
            if (this.isConnected) {
                this.isConnected = false;
                console.error('✗ API Disconnected');
                const enhancedMsg = this.enhanceErrorMessage('Lost connection to server', error);
                this.ui.error(enhancedMsg);
            }

            this.ui.updateStatusBadge('error', '✗ Disconnected');
        }
    }

    /**
     * Task #121: Start connection monitoring
     * Periodically checks API health to detect server disconnection
     */
    startConnectionMonitoring() {
        // Check every 5 seconds
        this.connectionCheckInterval = setInterval(async () => {
            await this.checkAPIHealth();
        }, 5000);

        console.log('Connection monitoring started (5s interval)');
    }

    /**
     * Task #121: Stop connection monitoring
     * Called when page is unloading
     */
    stopConnectionMonitoring() {
        if (this.connectionCheckInterval) {
            clearInterval(this.connectionCheckInterval);
            this.connectionCheckInterval = null;
            console.log('Connection monitoring stopped');
        }
    }

    /**
     * Check if this is first run and show welcome dialog
     */
    async checkFirstRun() {
        try {
            const response = await fetch('/api/config/first-run');
            const data = await response.json();

            if (data.first_run || !data.keys_configured) {
                this.showFirstRunDialog();
            }
        } catch (error) {
            console.error('Error checking first run:', error);
        }
    }

    /**
     * Show first-run welcome dialog
     */
    showFirstRunDialog() {
        const modal = document.getElementById('first-run-modal');
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';

        // Setup event listeners
        document.getElementById('first-run-save-btn').onclick = () => this.saveFirstRunSettings();
        document.getElementById('first-run-skip-btn').onclick = () => this.skipFirstRun();
    }

    /**
     * Save first-run settings
     */
    async saveFirstRunSettings() {
        const acoustidKey = document.getElementById('first-run-acoustid-key').value.trim();

        try {
            // Save config if key was provided
            if (acoustidKey) {
                const updates = { acoustid_api_key: acoustidKey };
                await fetch('/api/config/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ updates })
                });
            }

            // ALWAYS mark first run complete when user clicks "Save & Continue"
            // This prevents dialog from showing again, even if key was empty
            await fetch('/api/config/complete-first-run', { method: 'POST' });

            // Close dialog
            this.closeFirstRunDialog();
            const message = acoustidKey
                ? 'Settings saved! Enhanced metadata detection enabled.'
                : 'Setup complete! You can add API keys later in Settings ⚙️';
            this.ui.success(message);
        } catch (error) {
            this.ui.error('Failed to save settings: ' + error.message);
            console.error('Error saving first-run settings:', error);
        }
    }

    /**
     * Skip first-run configuration
     */
    async skipFirstRun() {
        try {
            // DO NOT mark first_run_complete when skipping
            // This allows dialog to show again if keys aren't configured
            this.closeFirstRunDialog();
            this.ui.info('Skipped for now. You can configure API keys in Settings ⚙️ anytime.');
        } catch (error) {
            console.error('Error skipping first run:', error);
        }
    }

    /**
     * Close first-run dialog
     */
    closeFirstRunDialog() {
        const modal = document.getElementById('first-run-modal');
        modal.classList.add('hidden');
        document.body.style.overflow = '';
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
    onDirectorySelected(path, filePaths = null) {
        // Fill the input with selected path
        document.getElementById('directory-path').value = path;

        // Task #84: Save last directory to config (asynchronously, don't block)
        this.saveLastDirectory(path).catch(error => {
            console.error('Failed to save last directory:', error);
            // Don't show error to user - non-critical background operation
        });

        // Store selected file paths if specific files were chosen
        this.selectedFilePaths = filePaths;

        // Automatically load the directory or specific files
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

        // Task #111: Clear per-album state immediately when loading new directory
        this.clearPerAlbumState();

        try {
            // Show loading state with skeleton
            this.ui.show('file-list-section');
            this.ui.show('file-list-skeleton');
            this.ui.hide('file-list-body');
            this.ui.hide('loading-files');
            this.ui.hide('no-files-message');
            document.getElementById('file-list-body').innerHTML = '';

            // Fetch directory contents RECURSIVELY (includes subdirectories)
            const result = await this.api.listDirectory(path, true);

            // Update state
            this.currentPath = result.path;
            this.currentFiles = result.files.filter(f => f.is_mp3);

            // If specific files were selected, filter to only those
            if (this.selectedFilePaths && this.selectedFilePaths.length > 0) {
                const selectedSet = new Set(this.selectedFilePaths);
                this.currentFiles = this.currentFiles.filter(f => selectedSet.has(f.path));
            }

            // Initialize filtered files (no search active yet)
            this.filteredFiles = [...this.currentFiles];
            this.searchQuery = '';

            // Clear search input if exists
            const searchInput = document.getElementById('file-search-input');
            const searchClearBtn = document.getElementById('search-clear-btn');
            if (searchInput) searchInput.value = '';
            if (searchClearBtn) searchClearBtn.classList.add('hidden');

            this.selectedFiles.clear();
            this.selectedFilePaths = null; // Clear after use

            // Task #94: Clear temporary template when loading new directory
            // This ensures Smart Track Detection template doesn't persist across folders
            this.temporaryTemplate = null;
            console.log('Cleared temporary template for new directory');

            // Task #105: Reset banner dismissal flag for new directory
            // This allows banner to appear again for the new directory
            this.smartBannerDismissedForCurrentLoad = false;

            // Update UI
            this.updateBreadcrumb(result.path);
            this.updateFileStats(result.total_files, result.mp3_count);

            // Hide skeleton loading
            this.ui.hide('file-list-skeleton');
            this.ui.hide('loading-files');

            if (this.currentFiles.length === 0) {
                this.ui.show('no-files-message');
            } else {
                this.ui.show('file-list-body');
                await this.renderFileList();
                this.ui.show('actions-section');
            }

            this.ui.success(`Loaded ${result.mp3_count} MP3 file(s)`);

        } catch (error) {
            this.ui.hide('file-list-skeleton');
            this.ui.hide('loading-files');
            this.ui.show('file-list-body');
            const enhancedMsg = this.enhanceErrorMessage('Failed to load directory', error);
            this.ui.error(enhancedMsg);
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

        // Initialize metadata loading progress
        this.metadataLoadState = {
            total: this.currentFiles.length,
            loaded: 0,
            startTime: Date.now(),
            estimatedTimeRemaining: null,
            currentFile: null
        };

        // Task #126: Create AbortController for cancellation support
        this.metadataAbortController = new AbortController();

        // Show progress indicator if we have files
        if (this.currentFiles.length > 0) {
            this.showMetadataProgress();
        }

        try {
            // Step 1: Create all rows (fast - just DOM creation)
            for (const file of this.currentFiles) {
                const row = await this.createFileRow(file);
                tbody.appendChild(row);
            }

            // Step 2: Load metadata sequentially with cancellation support
            // Task #126: This allows cancel to work properly by checking abort signal between each load
            for (const file of this.currentFiles) {
                // Check if cancelled before loading next file's metadata
                if (this.metadataAbortController && this.metadataAbortController.signal.aborted) {
                    console.log('[CANCEL] Metadata loading stopped after', this.metadataLoadState.loaded, 'files');
                    break;
                }

                // Load metadata for this file
                await this.loadFileMetadata(file.path, file._metadataCells);
            }

            // All metadata loaded successfully
            console.log('[METADATA] Completed loading', this.metadataLoadState.loaded, 'files');

        } catch (error) {
            // Handle abort error silently
            if (error.name === 'AbortError') {
                console.log('[CANCEL] Metadata loading aborted');
            } else {
                console.error('[METADATA] Error loading metadata:', error);
                this.ui.error('Error loading metadata: ' + error.message);
            }
        } finally {
            // Clean up abort controller and hide progress
            this.metadataAbortController = null;
            this.hideMetadataProgress();
        }

        // Update sort indicators after rendering
        this.updateSortIndicators();

        // Auto-load previews for reasonable directory sizes
        // For large directories (200+ files), user must manually click "Preview Rename"
        // This improves UX for typical use cases while avoiding performance issues for massive libraries
        const AUTO_PREVIEW_THRESHOLD = 200;
        if (this.currentFiles.length > 0 && this.currentFiles.length < AUTO_PREVIEW_THRESHOLD) {
            // Small directory - auto-load previews for better UX
            // Metadata is already loaded (sequentially above), so we can preview immediately
            console.log('[AUTO-PREVIEW] Directory size', this.currentFiles.length, '< threshold', AUTO_PREVIEW_THRESHOLD, '- auto-loading previews');

            // Auto-load previews - metadata is already loaded
            try {
                await this.loadAllPreviews();
                console.log(`✓ Auto-loaded previews for ${this.currentFiles.length} files`);
            } catch (error) {
                console.error('Preview auto-load failed:', error);
                // Don't show error - user can still manually preview
            }
        } else if (this.currentFiles.length >= AUTO_PREVIEW_THRESHOLD) {
            // Large directory - show hint that user needs to click Preview button
            console.log(`⚠ Directory has ${this.currentFiles.length} files - manual preview required (threshold: ${AUTO_PREVIEW_THRESHOLD})`);
        }

        // Analyze context and show smart suggestion (Task #55)
        // Task #126: Metadata is now loaded synchronously above, so we can run smart detection immediately
        // Task #105: Only show if not dismissed for current load
        // Banner reappears on page refresh or when loading different directory
        if (this.currentFiles.length > 0 && !this.smartBannerDismissedForCurrentLoad) {
            console.log('✓ All metadata loaded, running smart detection...');
            await this.analyzeAndShowSuggestion();
        }
    }

    /**
     * Sort and re-render files based on current sort state
     */
    async sortAndRenderFiles() {
        if (this.currentFiles.length === 0) return;

        // Sort files
        this.sortFiles();

        // Re-render table
        const tbody = document.getElementById('file-list-body');
        tbody.innerHTML = '';

        for (const file of this.currentFiles) {
            const row = await this.createFileRow(file);
            tbody.appendChild(row);
        }

        this.updateSortIndicators();
    }

    /**
     * Sort currentFiles array based on sort state
     */
    sortFiles() {
        const { column, direction } = this.sortState;
        const multiplier = direction === 'asc' ? 1 : -1;

        this.currentFiles.sort((a, b) => {
            let aVal, bVal;

            switch (column) {
                case 'name':
                    aVal = a.name.toLowerCase();
                    bVal = b.name.toLowerCase();
                    return aVal.localeCompare(bVal) * multiplier;

                case 'modified':
                    aVal = a.modified_time || 0;
                    bVal = b.modified_time || 0;
                    return (aVal - bVal) * multiplier;

                case 'size':
                    aVal = a.size || 0;
                    bVal = b.size || 0;
                    return (aVal - bVal) * multiplier;

                case 'bpm':
                    // Get BPM from metadata (need to parse or have it available)
                    aVal = a.metadata?.bpm ? parseInt(a.metadata.bpm) : 0;
                    bVal = b.metadata?.bpm ? parseInt(b.metadata.bpm) : 0;
                    return (aVal - bVal) * multiplier;

                case 'track':
                    // Get track number from metadata
                    aVal = a.metadata?.track ? parseInt(a.metadata.track) : 9999;
                    bVal = b.metadata?.track ? parseInt(b.metadata.track) : 9999;
                    return (aVal - bVal) * multiplier;

                // Task #106: Add sorting for new metadata columns
                case 'artist':
                    aVal = (a.metadata?.artist || '').toLowerCase();
                    bVal = (b.metadata?.artist || '').toLowerCase();
                    return aVal.localeCompare(bVal) * multiplier;

                case 'title':
                    aVal = (a.metadata?.title || '').toLowerCase();
                    bVal = (b.metadata?.title || '').toLowerCase();
                    return aVal.localeCompare(bVal) * multiplier;

                case 'album':
                    aVal = (a.metadata?.album || '').toLowerCase();
                    bVal = (b.metadata?.album || '').toLowerCase();
                    return aVal.localeCompare(bVal) * multiplier;

                case 'year':
                    aVal = a.metadata?.year ? parseInt(a.metadata.year) : 0;
                    bVal = b.metadata?.year ? parseInt(b.metadata.year) : 0;
                    return (aVal - bVal) * multiplier;

                case 'genre':
                    aVal = (a.metadata?.genre || '').toLowerCase();
                    bVal = (b.metadata?.genre || '').toLowerCase();
                    return aVal.localeCompare(bVal) * multiplier;

                case 'duration':
                    // Parse duration string "4:23" to seconds for sorting
                    const parseDuration = (dur) => {
                        if (!dur) return 0;
                        const parts = dur.split(':');
                        if (parts.length === 2) {
                            return parseInt(parts[0]) * 60 + parseInt(parts[1]);
                        }
                        return 0;
                    };
                    aVal = parseDuration(a.metadata?.duration);
                    bVal = parseDuration(b.metadata?.duration);
                    return (aVal - bVal) * multiplier;

                case 'key':
                    aVal = (a.metadata?.key || '').toLowerCase();
                    bVal = (b.metadata?.key || '').toLowerCase();
                    return aVal.localeCompare(bVal) * multiplier;

                default:
                    return 0;
            }
        });
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

        // Current Filename (show relative path for subdirectories)
        const currentCell = document.createElement('td');
        currentCell.className = 'col-current';

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
                currentCell.innerHTML = `<span style="color: var(--text-secondary);">${subdir}/</span>${filename}`;
            } else {
                currentCell.textContent = cleanPath;
            }
        } else {
            currentCell.textContent = file.name;
        }

        currentCell.title = file.path;  // Full path on hover
        row.appendChild(currentCell);

        // Preview Filename (will auto-load for small directories)
        const previewCell = document.createElement('td');
        previewCell.className = 'col-preview';
        // Show appropriate placeholder based on directory size
        const AUTO_PREVIEW_THRESHOLD = 200;
        if (this.currentFiles.length < AUTO_PREVIEW_THRESHOLD) {
            // Small directory - will auto-load
            previewCell.innerHTML = '<span class="preview-loading">(loading...)</span>';
        } else {
            // Large directory - requires manual preview
            previewCell.innerHTML = '<span class="preview-pending" style="color: var(--text-secondary);">—</span>';
        }
        row.appendChild(previewCell);

        // Store reference to preview cell for later update
        file._previewCell = previewCell;

        // Metadata cells (will load on demand)
        const artistCell = document.createElement('td');
        artistCell.className = 'col-artist';
        artistCell.textContent = '...';
        row.appendChild(artistCell);

        const titleCell = document.createElement('td');
        titleCell.className = 'col-title';
        titleCell.textContent = '...';
        row.appendChild(titleCell);

        // Task #106: Add new metadata columns
        const albumCell = document.createElement('td');
        albumCell.className = 'col-album';
        albumCell.textContent = '...';
        row.appendChild(albumCell);

        const yearCell = document.createElement('td');
        yearCell.className = 'col-year';
        yearCell.textContent = '...';
        row.appendChild(yearCell);

        const genreCell = document.createElement('td');
        genreCell.className = 'col-genre';
        genreCell.textContent = '...';
        row.appendChild(genreCell);

        const durationCell = document.createElement('td');
        durationCell.className = 'col-duration';
        durationCell.textContent = '...';
        row.appendChild(durationCell);

        const bpmCell = document.createElement('td');
        bpmCell.className = 'col-bpm';
        bpmCell.textContent = '...';
        row.appendChild(bpmCell);

        const keyCell = document.createElement('td');
        keyCell.className = 'col-key';
        keyCell.textContent = '...';
        row.appendChild(keyCell);

        // Source column
        const sourceCell = document.createElement('td');
        sourceCell.className = 'col-source';
        sourceCell.innerHTML = '<span style="color: var(--text-muted);">...</span>';
        row.appendChild(sourceCell);

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

        // Task #126: Don't load metadata here - will be loaded after all rows are created
        // This allows cancellation to work properly

        // Store cell references for later metadata loading
        file._metadataCells = { artistCell, titleCell, albumCell, yearCell, genreCell, durationCell, bpmCell, keyCell, sourceCell };

        // Store preview cell reference for later updates
        file._previewCell = previewCell;

        return row;
    }

    /**
     * Load metadata for a file
     * Task #126: Added abort signal support
     */
    async loadFileMetadata(path, cells) {
        try {
            // Task #126: Check if cancelled before making API call
            if (this.metadataAbortController && this.metadataAbortController.signal.aborted) {
                throw new DOMException('Metadata loading cancelled', 'AbortError');
            }

            // Update current file being processed
            const fileName = path.split('/').pop();
            this.metadataLoadState.currentFile = fileName;
            this.updateMetadataProgressText();

            // Task #126: Pass abort signal to API call if available
            const result = await this.api.getFileMetadata(
                path,
                this.metadataAbortController ? this.metadataAbortController.signal : undefined
            );
            const meta = result.metadata;

            // Store metadata in file object for sorting
            const file = this.currentFiles.find(f => f.path === path);
            if (file) {
                file.metadata = meta;
            }

            // Update cells with tooltips for full text
            cells.artistCell.textContent = meta.artist || '-';
            if (meta.artist) {
                cells.artistCell.title = `Artist: ${meta.artist}`;
            }

            cells.titleCell.textContent = meta.title || '-';
            if (meta.title) {
                cells.titleCell.title = `Title: ${meta.title}`;
            }

            // Task #106: Populate new metadata columns
            cells.albumCell.textContent = meta.album || '-';
            if (meta.album) {
                cells.albumCell.title = `Album: ${meta.album}`;
            }

            cells.yearCell.textContent = meta.year || '-';
            if (meta.year) {
                cells.yearCell.title = `Year: ${meta.year}`;
            }

            cells.genreCell.textContent = meta.genre || '-';
            if (meta.genre) {
                cells.genreCell.title = `Genre: ${meta.genre}`;
            }

            cells.durationCell.textContent = meta.duration || '-';
            if (meta.duration) {
                cells.durationCell.title = `Duration: ${meta.duration}`;
            }

            cells.bpmCell.textContent = meta.bpm || '-';
            if (meta.bpm) {
                cells.bpmCell.title = `BPM: ${meta.bpm}`;
            }

            cells.keyCell.textContent = meta.key || '-';
            if (meta.key) {
                // Add Camelot in parentheses if available
                if (meta.camelot) {
                    cells.keyCell.textContent += ` (${meta.camelot})`;
                    cells.keyCell.title = `Key: ${meta.key} (Camelot: ${meta.camelot})`;
                } else {
                    cells.keyCell.title = `Key: ${meta.key}`;
                }
            }

            // Update source column with metadata sources
            this.updateSourceCell(cells.sourceCell, meta);

        } catch (error) {
            console.error(`Failed to load metadata for ${path}:`, error);
            cells.artistCell.textContent = '?';
            cells.titleCell.textContent = '?';
            cells.albumCell.textContent = '?';  // Task #106
            cells.yearCell.textContent = '?';  // Task #106
            cells.genreCell.textContent = '?';  // Task #106
            cells.durationCell.textContent = '?';  // Task #106
            cells.bpmCell.textContent = '?';
            cells.keyCell.textContent = '?';
            cells.sourceCell.innerHTML = '<span style="color: var(--error);">Error</span>';
        } finally {
            // Update progress regardless of success/failure
            this.updateMetadataProgress();
        }
    }

    /**
     * Update source cell with metadata source badges
     */
    updateSourceCell(sourceCell, metadata) {
        // Collect unique sources from metadata
        const sources = new Set();
        if (metadata.artist_source) sources.add(metadata.artist_source);
        if (metadata.title_source) sources.add(metadata.title_source);
        if (metadata.bpm_source) sources.add(metadata.bpm_source);
        if (metadata.key_source) sources.add(metadata.key_source);

        // If no sources, show "-"
        if (sources.size === 0) {
            sourceCell.textContent = '-';
            return;
        }

        // Create badges container
        const container = document.createElement('div');
        container.className = 'metadata-sources';

        sources.forEach(source => {
            const badge = document.createElement('span');
            badge.className = 'metadata-badge';

            if (source === 'Tags') {
                badge.classList.add('source-tags');
                badge.textContent = '🏷️ ID3';
            } else if (source === 'MusicBrainz') {
                badge.classList.add('source-musicbrainz');
                badge.textContent = '🎵 MB';
            } else if (source === 'AI Audio') {
                badge.classList.add('source-ai');
                badge.textContent = '🤖 AI';
            } else {
                // Generic fallback
                badge.classList.add('source-tags');
                badge.textContent = source;
            }

            container.appendChild(badge);
        });

        sourceCell.innerHTML = '';
        sourceCell.appendChild(container);
    }

    /**
     * Show metadata progress indicator
     */
    showMetadataProgress() {
        const progressDiv = document.getElementById('metadata-progress');
        this.ui.show('metadata-progress');
        this.updateMetadataProgressText();
    }

    /**
     * Update metadata loading progress
     */
    updateMetadataProgress() {
        this.metadataLoadState.loaded++;
        this.updateMetadataProgressText();

        // Hide progress indicator when all metadata is loaded
        if (this.metadataLoadState.loaded >= this.metadataLoadState.total) {
            setTimeout(() => {
                this.hideMetadataProgress();
            }, 1000); // Keep visible for 1 second after completion
        }
    }

    /**
     * Update progress text with percentage and time estimate
     */
    updateMetadataProgressText() {
        const { total, loaded, startTime, currentFile } = this.metadataLoadState;
        const progressText = document.getElementById('metadata-progress-text');
        const progressBar = document.getElementById('metadata-progress-bar');
        const currentFileName = document.getElementById('metadata-current-file-name');

        if (!progressText) return;

        const percentage = total > 0 ? Math.round((loaded / total) * 100) : 0;

        // Update progress bar width and ARIA attribute
        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
            const container = progressBar.parentElement;
            if (container) {
                container.setAttribute('aria-valuenow', percentage);
            }
        }

        // Update current file name
        if (currentFileName && currentFile) {
            currentFileName.textContent = currentFile;
        }

        // Calculate estimated time remaining
        let timeRemainingText = 'calculating...';
        if (loaded > 0 && loaded < total) {
            const elapsed = (Date.now() - startTime) / 1000; // seconds
            const avgTimePerFile = elapsed / loaded;
            const remaining = (total - loaded) * avgTimePerFile;

            if (remaining < 60) {
                timeRemainingText = `~${Math.ceil(remaining)}s remaining`;
            } else {
                const minutes = Math.floor(remaining / 60);
                const seconds = Math.ceil(remaining % 60);
                timeRemainingText = `~${minutes}m ${seconds}s remaining`;
            }
        } else if (loaded >= total) {
            timeRemainingText = 'complete!';
        }

        progressText.textContent = `Loading metadata: ${loaded}/${total} files (${percentage}%) - ${timeRemainingText}`;
    }

    /**
     * Hide metadata progress indicator
     */
    hideMetadataProgress() {
        this.ui.hide('metadata-progress');
    }

    /**
     * Cancel metadata loading or preview generation operation (Tasks #126, #127)
     */
    cancelMetadataLoading() {
        console.log('[CANCEL] Operation cancelled by user');

        // Determine which operation is running
        let operationType = 'metadata';
        let loaded = 0;
        let total = 0;

        // Check if preview operation is running
        if (this.previewAbortController && this.previewLoadState) {
            operationType = 'preview';
            loaded = this.previewLoadState.loaded;
            total = this.previewLoadState.total;

            // Abort preview operation
            this.previewAbortController.abort();
            this.previewAbortController = null;
            this.hidePreviewProgress();

            console.log(`[CANCEL] Preview generation cancelled: ${loaded}/${total} files`);
        }
        // Otherwise check if metadata operation is running
        else if (this.metadataAbortController && this.metadataLoadState) {
            operationType = 'metadata';
            loaded = this.metadataLoadState.loaded;
            total = this.metadataLoadState.total;

            // Abort metadata operation
            this.metadataAbortController.abort();
            this.metadataAbortController = null;
            this.hideMetadataProgress();

            console.log(`[CANCEL] Metadata loading cancelled: ${loaded}/${total} files`);
        }

        // Show notification with loaded count
        const operationLabel = operationType === 'preview' ? 'Preview generation' : 'Metadata loading';
        const message = loaded > 0
            ? `${operationLabel} cancelled - ${loaded}/${total} files processed`
            : `${operationLabel} cancelled`;

        this.ui.warning(message);
    }

    /**
     * Show a toast notification (Task #130)
     * @param {Object} options - Toast options
     * @param {string} options.type - Toast type: 'success', 'info', 'warning', 'error'
     * @param {string} options.title - Toast title
     * @param {string} options.message - Toast message
     * @param {Array} options.actions - Array of action buttons: [{label, callback, primary}]
     * @param {number} options.duration - Auto-dismiss duration in ms (0 = no auto-dismiss)
     */
    showToast({ type = 'info', title, message, actions = [], duration = 5000 }) {
        const container = document.getElementById('toast-container');
        if (!container) {
            console.error('[TOAST] Toast container not found');
            return;
        }

        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;

        // Icon based on type
        const icons = {
            success: '✓',
            info: 'ℹ️',
            warning: '⚠️',
            error: '✗'
        };
        const icon = icons[type] || icons.info;

        // Build toast HTML
        let html = `
            <div class="toast-header">
                <span class="toast-icon">${icon}</span>
                <span class="toast-title">${this.escapeHtml(title)}</span>
                <button class="toast-close" aria-label="Close">×</button>
            </div>
        `;

        if (message) {
            html += `<div class="toast-message">${this.escapeHtml(message)}</div>`;
        }

        if (actions.length > 0) {
            html += '<div class="toast-actions">';
            actions.forEach(action => {
                const btnClass = action.primary ? 'toast-btn toast-btn-primary' : 'toast-btn toast-btn-secondary';
                html += `<button class="${btnClass}" data-action="${action.label}">${this.escapeHtml(action.label)}</button>`;
            });
            html += '</div>';
        }

        toast.innerHTML = html;

        // Close button handler
        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => {
            this.dismissToast(toast);
        });

        // Action button handlers
        actions.forEach(action => {
            const btn = toast.querySelector(`[data-action="${action.label}"]`);
            if (btn) {
                btn.addEventListener('click', () => {
                    action.callback();
                    this.dismissToast(toast);
                });
            }
        });

        // Add to container
        container.appendChild(toast);

        // Auto-dismiss if duration > 0
        if (duration > 0) {
            setTimeout(() => {
                this.dismissToast(toast);
            }, duration);
        }

        console.log(`[TOAST] Shown: ${type} - ${title}`);
    }

    /**
     * Dismiss a toast notification (Task #130)
     */
    dismissToast(toast) {
        if (!toast || !toast.parentElement) return;

        // Add hiding animation
        toast.classList.add('toast-hiding');

        // Remove after animation completes
        setTimeout(() => {
            if (toast.parentElement) {
                toast.parentElement.removeChild(toast);
            }
        }, 300);
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Load preview (proposed) filenames for all files in the current list
     */
    async loadAllPreviews() {
        if (!this.currentPath || this.currentFiles.length === 0) {
            this.ui.warning('No files loaded to preview');
            return;
        }

        // Initialize preview progress state
        this.previewLoadState = {
            total: this.currentFiles.length,
            loaded: 0,
            startTime: Date.now()
        };

        try {
            // Task #89: Create AbortController for cancellation support
            this.previewAbortController = new AbortController();

            // Show progress indicator (Bug fix #76 - moved inside try-catch)
            this.showPreviewProgress();

            // Task #111: Check if per-album mode is active
            if (this.perAlbumTemplates && Object.keys(this.perAlbumTemplates).length > 0) {
                console.log('[PER_ALBUM] Generating previews with per-album templates');
                await this.loadPreviewsPerAlbum();
            } else {
                // Standard single-template preview loading
                await this.loadPreviewsSingleTemplate();
            }

            // Hide progress after 1 second
            setTimeout(() => {
                this.hidePreviewProgress();
            }, 1000);

        } catch (error) {
            // Task #89: Handle cancellation separately
            if (error.name === 'AbortError') {
                console.log('Preview loading was cancelled');
                // Don't show error - cancellation is intentional
            } else {
                console.error('Failed to load previews:', error);
                this.ui.error(`Failed to load previews: ${error.message}`);
            }
            this.hidePreviewProgress();
        } finally {
            // Task #89: Clean up abort controller
            this.previewAbortController = null;
        }
    }

    /**
     * Load previews with single template (standard mode)
     */
    async loadPreviewsSingleTemplate() {
        // Get current template: Check for temporary template first (Task #94), then settings
        let template;
        if (this.temporaryTemplate) {
            template = this.temporaryTemplate;
            console.log('Using temporary template from Smart Track Detection:', template);
        } else {
            const config = await this.api.getConfig();
            template = config.default_template || null;
            console.log('Using template from settings:', template);
        }

        // Get all file paths
        const filePaths = this.currentFiles.map(f => f.path);

        // Update progress: "Fetching previews..."
        this.updatePreviewProgressText('Fetching previews from server...');

        // Call preview API (Task #89: with cancellation signal)
        const result = await this.api.previewRename(
            this.currentPath,
            false, // recursive (not needed - we have specific file paths)
            template,
            filePaths,
            false, // enhance_metadata = false (just use existing metadata)
            this.previewAbortController.signal // Task #89: cancellation support
        );

        // Update preview cells for each file with progress updates
        for (let i = 0; i < result.previews.length; i++) {
            const preview = result.previews[i];
            const file = this.currentFiles.find(f => f.path === preview.src);

            if (file && file._previewCell) {
                this.updatePreviewCell(file._previewCell, preview, file.path);
            }

            // Update progress
            this.previewLoadState.loaded = i + 1;
            const filename = preview.src.split('/').pop();
            this.updatePreviewProgressText(`Processing: ${filename}`);

            // Small delay to show progress (visual feedback)
            if (i % 10 === 0) { // Update UI every 10 files
                await new Promise(resolve => setTimeout(resolve, 10));
            }
        }

        this.ui.success(`Loaded previews for ${result.total} file(s)`);
    }

    /**
     * Load previews with per-album templates (Task #111)
     */
    async loadPreviewsPerAlbum() {
        // Get global template for unselected albums
        const config = await this.api.getConfig();
        const globalTemplate = config.default_template || '';

        // Group files by album
        const albumFiles = {};
        const orphanFiles = [];

        for (const file of this.currentFiles) {
            const albumPath = this.getAlbumPathForFile(file.path);

            if (albumPath) {
                if (!albumFiles[albumPath]) {
                    albumFiles[albumPath] = [];
                }
                albumFiles[albumPath].push(file);
            } else {
                orphanFiles.push(file);
            }
        }

        this.updatePreviewProgressText('Fetching previews per album...');

        let totalLoaded = 0;

        // Load previews for each album with its template
        for (const [albumPath, files] of Object.entries(albumFiles)) {
            const template = this.perAlbumTemplates[albumPath] || globalTemplate;
            const filePaths = files.map(f => f.path);

            console.log(`[PER_ALBUM] Loading previews for ${albumPath} with template: ${template}`);

            try {
                const result = await this.api.previewRename(
                    this.currentPath,
                    false,
                    template,
                    filePaths,
                    false,
                    this.previewAbortController.signal
                );

                // Update preview cells
                for (const preview of result.previews) {
                    const file = files.find(f => f.path === preview.src);
                    if (file && file._previewCell) {
                        this.updatePreviewCell(file._previewCell, preview, file.path);
                    }

                    totalLoaded++;
                    this.previewLoadState.loaded = totalLoaded;
                    const filename = preview.src.split('/').pop();
                    this.updatePreviewProgressText(`Processing: ${filename}`);
                }
            } catch (error) {
                if (error.name === 'AbortError') throw error;
                console.error(`[PER_ALBUM] Preview failed for ${albumPath}:`, error);
            }
        }

        // Load previews for orphan files with global template
        if (orphanFiles.length > 0) {
            const filePaths = orphanFiles.map(f => f.path);

            try {
                const result = await this.api.previewRename(
                    this.currentPath,
                    false,
                    globalTemplate,
                    filePaths,
                    false,
                    this.previewAbortController.signal
                );

                for (const preview of result.previews) {
                    const file = orphanFiles.find(f => f.path === preview.src);
                    if (file && file._previewCell) {
                        this.updatePreviewCell(file._previewCell, preview, file.path);
                    }

                    totalLoaded++;
                    this.previewLoadState.loaded = totalLoaded;
                }
            } catch (error) {
                if (error.name === 'AbortError') throw error;
                console.error('[PER_ALBUM] Preview failed for orphan files:', error);
            }
        }

        this.ui.success(`Loaded previews for ${totalLoaded} file(s) across ${Object.keys(albumFiles).length} albums`);
    }

    /**
     * Show preview progress indicator
     */
    showPreviewProgress() {
        const progressDiv = document.getElementById('metadata-progress');
        if (progressDiv) {
            this.ui.show('metadata-progress');
            this.updatePreviewProgressText('Starting preview generation...');
        }
    }

    /**
     * Update preview progress text
     */
    updatePreviewProgressText(currentFile = '') {
        if (!this.previewLoadState) return;

        const { total, loaded, startTime } = this.previewLoadState;
        const progressText = document.getElementById('metadata-progress-text');

        if (!progressText) return;

        const percentage = total > 0 ? Math.round((loaded / total) * 100) : 0;

        // Calculate estimated time remaining
        let timeRemainingText = 'calculating...';
        if (loaded > 0 && loaded < total) {
            const elapsed = (Date.now() - startTime) / 1000; // seconds
            const avgTimePerFile = elapsed / loaded;
            const remaining = (total - loaded) * avgTimePerFile;

            if (remaining < 60) {
                timeRemainingText = `~${Math.ceil(remaining)}s remaining`;
            } else {
                const minutes = Math.floor(remaining / 60);
                const seconds = Math.ceil(remaining % 60);
                timeRemainingText = `~${minutes}m ${seconds}s remaining`;
            }
        } else if (loaded >= total) {
            timeRemainingText = 'complete!';
        }

        progressText.textContent = `Loading previews: ${loaded}/${total} files (${percentage}%) - ${timeRemainingText}${currentFile ? ' - ' + currentFile : ''}`;
    }

    /**
     * Hide preview progress indicator
     */
    hidePreviewProgress() {
        this.ui.hide('metadata-progress');
        this.previewLoadState = null;
    }

    /**
     * Update a single preview cell with preview data
     */
    updatePreviewCell(cell, preview, srcPath) {
        // Extract just the filename from paths
        const getFilename = (path) => path.split('/').pop();

        const srcFilename = getFilename(srcPath);
        const dstFilename = preview.dst ? getFilename(preview.dst) : null;

        if (preview.status === 'will_skip') {
            // Will skip - show reason
            cell.innerHTML = `<span class="preview-same" title="${preview.reason}">(no change: ${preview.reason})</span>`;
        } else if (preview.status === 'will_rename' && dstFilename) {
            // Will rename - check if same as current
            if (dstFilename === srcFilename) {
                cell.innerHTML = `<span class="preview-same">(same)</span>`;
            } else {
                // Different name - highlight in green
                cell.innerHTML = `<span class="preview-new" title="Will rename to: ${dstFilename}">${dstFilename}</span>`;
            }
        } else if (preview.status === 'error') {
            // Error
            cell.innerHTML = `<span style="color: var(--error);" title="${preview.reason}">Error</span>`;
        } else {
            // Unknown status
            cell.innerHTML = `<span class="preview-placeholder">-</span>`;
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
     * Toggle select all files (only visible/filtered files)
     */
    toggleSelectAll(checked) {
        const checkboxes = document.querySelectorAll('input[type="checkbox"][data-path]');
        checkboxes.forEach(cb => {
            // Only select/deselect visible rows (respects search filter)
            const row = cb.closest('tr');
            if (row && !row.classList.contains('hidden')) {
                cb.checked = checked;
                if (checked) {
                    this.selectedFiles.add(cb.dataset.path);
                } else {
                    this.selectedFiles.delete(cb.dataset.path);
                }
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
        const floatingBar = document.getElementById('floating-action-bar');
        const floatingPreviewBtn = document.getElementById('floating-preview-btn');
        const floatingRenameBtn = document.getElementById('floating-rename-btn');
        const floatingCount = document.getElementById('floating-selection-count');
        const floatingRenameText = document.getElementById('floating-rename-text');

        // Only use selected files count - no fallback to all files
        // This ensures buttons are disabled when user explicitly unchecks all files
        const fileCount = this.selectedFiles.size;

        if (fileCount > 0) {
            // Update bottom buttons
            previewBtn.disabled = false;
            previewBtn.textContent = `👁️ Preview Rename (${fileCount} files)`;

            renameNowBtn.disabled = false;
            renameNowBtn.textContent = `✅ Rename Now (${fileCount} files)`;

            // Show and update floating action bar
            floatingBar.classList.remove('hidden');
            floatingCount.textContent = `${fileCount} file${fileCount === 1 ? '' : 's'} selected`;
            floatingRenameText.textContent = `Rename Now (${fileCount})`;
            floatingPreviewBtn.disabled = false;
            floatingRenameBtn.disabled = false;
        } else {
            // Update bottom buttons
            previewBtn.disabled = true;
            previewBtn.textContent = '👁️ Preview Rename';

            renameNowBtn.disabled = true;
            renameNowBtn.textContent = '✅ Rename Now';

            // Hide floating action bar
            floatingBar.classList.add('hidden');
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
            // First, auto-load preview names into the table column
            await this.loadAllPreviews();

            // Show preview modal
            const modal = document.getElementById('preview-modal');
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';

            // Show loading
            this.ui.show('preview-loading');
            this.ui.hide('preview-list');
            this.ui.hide('preview-empty');

            // Get selected file paths
            const filePaths = Array.from(this.selectedFiles);

            // Call preview API (we already have the data, but get it again for the modal)
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
            const enhancedMsg = this.enhanceErrorMessage('Failed to generate preview', error);
            this.ui.error(enhancedMsg);
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

        // Create filename comparison section
        const filenameSection = document.createElement('div');
        filenameSection.className = 'preview-filenames';

        // Original name
        const originalName = preview.src.split('/').pop();
        const originalDiv = document.createElement('div');
        originalDiv.className = 'preview-original';
        originalDiv.innerHTML = `<strong class="preview-label">Current:</strong> <span class="filename-old">${originalName}</span>`;
        filenameSection.appendChild(originalDiv);

        // New name or reason
        if (preview.status === 'will_rename') {
            const newName = preview.dst.split('/').pop();
            const newDiv = document.createElement('div');
            newDiv.className = 'preview-new';
            newDiv.innerHTML = `<strong class="preview-label">New:</strong> <span class="filename-new">${newName}</span>`;
            filenameSection.appendChild(newDiv);
        }

        info.appendChild(filenameSection);

        // Add reason for non-rename status
        if (preview.status === 'will_rename') {
            // Keep existing metadata sources rendering below

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
            // Task #94 FIX v16: Check for temporary template first, then settings
            let template;
            if (this.temporaryTemplate) {
                template = this.temporaryTemplate;
                console.log('Using temporary template from Smart Track Detection for rename:', template);
            } else {
                const config = await this.api.getConfig();
                template = config.default_template || null;
                console.log('Using template from settings for rename:', template);
            }

            // Start rename operation with template
            const result = await this.api.executeRename(this.currentPath, filePaths, template);
            const operationId = result.operation_id;

            // Poll for progress
            await this.pollOperationProgress(operationId);

        } catch (error) {
            const enhancedMsg = this.enhanceErrorMessage('Failed to start rename operation', error);
            this.ui.error(enhancedMsg);
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

        // Store undo session ID if available
        if (status.undo_session_id) {
            this.lastRenameSessionId = status.undo_session_id;
        }

        // Show done button, hide cancel
        document.getElementById('progress-cancel-btn').classList.add('hidden');
        const doneBtn = document.getElementById('progress-done-btn');
        doneBtn.classList.remove('hidden');
        doneBtn.onclick = () => {
            this.closeProgressOverlay();

            // Task #98: Hide Smart Track Detection banner after successful rename
            // Action complete - banner no longer needed
            if (results.renamed > 0) {
                this.hideSmartSuggestion();
                this.smartBannerDismissedForCurrentLoad = true;
                console.log('[Task #98] Banner hidden after successful rename');
            }

            // Show undo toast if files were renamed
            if (results.renamed > 0 && this.lastRenameSessionId) {
                this.ui.showUndoToast(
                    `✅ Successfully renamed ${results.renamed} file${results.renamed !== 1 ? 's' : ''}`,
                    () => this.undoRename(this.lastRenameSessionId),
                    30  // 30 seconds
                );
            } else {
                // No renamed files, just show regular success
                this.ui.success(`Operation completed: ${results.renamed} renamed, ${results.skipped} skipped`);
            }

            this.loadDirectory(); // Refresh file list
        };
    }

    /**
     * Undo last rename operation
     * @param {string} sessionId - Undo session ID
     */
    async undoRename(sessionId) {
        try {
            const result = await this.api.undoRename(sessionId);

            if (result.success) {
                this.ui.success(`✅ Undo successful - ${result.reverted_count} file${result.reverted_count !== 1 ? 's' : ''} restored`);

                if (result.error_count > 0) {
                    this.ui.warning(`⚠️ ${result.error_count} file${result.error_count !== 1 ? 's' : ''} could not be reverted`);
                }

                // Reload directory to show reverted files
                await this.loadDirectory();

                // Clear last session ID
                this.lastRenameSessionId = null;
            }
        } catch (error) {
            const enhancedMsg = this.enhanceErrorMessage('Failed to undo rename', error);
            this.ui.error(enhancedMsg);
            console.error('Undo error:', error);
        }
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

        // Task #97: Clear all selection state after rename completes
        // This ensures Select All checkbox and individual checkboxes are in sync
        this.selectedFiles.clear();
        const selectAllCheckbox = document.getElementById('select-all');
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = false;
        }
        // Update button states
        this.updatePreviewButton();

        // Reload directory to show updated filenames (after rename)
        if (this.currentPath) {
            this.loadDirectory();
        }
    }

    /**
     * Show rename confirmation dialog
     */
    showRenameConfirmation() {
        if (!this.currentPath) {
            this.ui.warning('Please select a directory first');
            return;
        }

        // Only use selected files - no fallback
        const fileCount = this.selectedFiles.size;

        if (fileCount === 0) {
            this.ui.warning('No files selected. Please select files to rename.');
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
        // Get selected file paths only
        const filePaths = Array.from(this.selectedFiles);

        if (filePaths.length === 0) {
            this.ui.warning('No files selected. Please select files to rename.');
            return;
        }

        // Show progress overlay
        this.showProgressOverlay(filePaths.length);

        try {
            // Task #94 FIX v16: Check for temporary template first, then settings
            let template;
            if (this.temporaryTemplate) {
                template = this.temporaryTemplate;
                console.log('Using temporary template from Smart Track Detection for rename:', template);
            } else {
                const config = await this.api.getConfig();
                template = config.default_template || null;
                console.log('Using template from settings for rename:', template);
            }

            // Start rename operation with template
            const result = await this.api.executeRename(this.currentPath, filePaths, template);
            const operationId = result.operation_id;

            // Poll for progress
            await this.pollOperationProgress(operationId);

        } catch (error) {
            const enhancedMsg = this.enhanceErrorMessage('Failed to start rename operation', error);
            this.ui.error(enhancedMsg);
            console.error('Execute error:', error);
            this.closeProgressOverlay();
        }
    }

    /**
     * Show settings modal
     */
    async showSettings() {
        try {
            // Show modal
            const modal = document.getElementById('settings-modal');
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';

            // Load current settings
            await this.loadSettings();

            // Setup event listeners
            this.setupSettingsListeners();

        } catch (error) {
            this.ui.error(`Failed to load settings: ${error.message}`);
            console.error('Settings error:', error);
        }
    }

    /**
     * Load settings from API
     */
    async loadSettings() {
        try {
            const config = await this.api.getConfig();

            // Populate form fields
            document.getElementById('acoustid-api-key').value = config.acoustid_api_key || '';
            document.getElementById('enable-musicbrainz').checked = config.enable_musicbrainz || false;
            document.getElementById('auto-detect-bpm').checked = config.auto_detect_bpm !== false;
            document.getElementById('auto-detect-key').checked = config.auto_detect_key !== false;
            document.getElementById('use-mb-for-all-fields').checked = config.use_mb_for_all_fields !== false;
            document.getElementById('verify-mode').checked = config.verify_mode || false;
            document.getElementById('default-template').value = config.default_template || '{artist} - {title} [{camelot} {bpm}]';
            document.getElementById('recursive-default').checked = config.recursive_default !== false;
            document.getElementById('track-number-padding').value = config.track_number_padding !== undefined ? config.track_number_padding : 2;
            document.getElementById('enable-smart-detection').checked = config.enable_smart_detection || false;
            document.getElementById('enable-per-album-detection').checked = config.enable_per_album_detection || false; // Task #108
            document.getElementById('remember-last-directory').checked = config.remember_last_directory !== false; // Task #84

            // Update template preview
            this.updateTemplatePreview();

        } catch (error) {
            console.error('Error loading settings:', error);
            this.ui.error('Failed to load settings');
        }
    }

    /**
     * Setup settings modal listeners
     */
    setupSettingsListeners() {
        // Close button
        const closeBtn = document.querySelector('#settings-modal .modal-close');
        closeBtn.onclick = () => this.closeSettings();

        // Cancel button
        const cancelBtn = document.getElementById('settings-cancel-btn');
        cancelBtn.onclick = () => this.closeSettings();

        // Overlay click
        const overlay = document.querySelector('#settings-modal .modal-overlay');
        overlay.onclick = () => this.closeSettings();

        // Save button
        const saveBtn = document.getElementById('settings-save-btn');
        saveBtn.onclick = () => this.saveSettings();

        // Reset button
        const resetBtn = document.getElementById('settings-reset-btn');
        resetBtn.onclick = () => this.resetSettings();

        // Template preview on input
        const templateInput = document.getElementById('default-template');
        templateInput.oninput = () => this.updateTemplatePreview();

        // Template preset selection
        const presetSelect = document.getElementById('template-preset');
        presetSelect.onchange = (e) => {
            if (e.target.value) {
                templateInput.value = e.target.value;
                this.updateTemplatePreview();
                // Reset preset selector
                setTimeout(() => {
                    presetSelect.value = '';
                }, 100);
            }
        };

        // Variable button clicks and drag-and-drop
        const variableBtns = document.querySelectorAll('.variable-btn');
        variableBtns.forEach(btn => {
            // Click to insert at cursor
            btn.onclick = () => {
                const variable = btn.dataset.variable;
                this.insertVariableAtCursor(templateInput, variable);
                this.updateTemplatePreview();
            };

            // Make draggable
            btn.draggable = true;
            btn.ondragstart = (e) => {
                e.dataTransfer.setData('text/plain', btn.dataset.variable);
                e.dataTransfer.effectAllowed = 'copy';
                btn.classList.add('dragging');
            };
            btn.ondragend = () => {
                btn.classList.remove('dragging');
            };
        });

        // Make template input accept drops
        templateInput.ondragover = (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
            templateInput.classList.add('drag-over');
        };
        templateInput.ondragleave = () => {
            templateInput.classList.remove('drag-over');
        };
        templateInput.ondrop = (e) => {
            e.preventDefault();
            templateInput.classList.remove('drag-over');

            const variable = e.dataTransfer.getData('text/plain');
            if (variable) {
                // Calculate drop position in text
                const rect = templateInput.getBoundingClientRect();
                const x = e.clientX - rect.left;

                // Estimate character position from pixel position
                const charWidth = 8; // Approximate character width
                const textLength = templateInput.value.length;
                const estimatedPos = Math.min(
                    Math.round(x / charWidth),
                    textLength
                );

                // Insert at estimated position
                const text = templateInput.value;
                templateInput.value = text.substring(0, estimatedPos) + variable + text.substring(estimatedPos);

                // Set cursor after inserted variable
                const cursorPos = estimatedPos + variable.length;
                templateInput.setSelectionRange(cursorPos, cursorPos);
                templateInput.focus();

                this.updateTemplatePreview();
            }
        };

        // Keyboard shortcuts
        const modal = document.getElementById('settings-modal');
        modal.onkeydown = (e) => {
            if (e.key === 'Escape') this.closeSettings();
        };
    }

    /**
     * Insert variable at cursor position in template input
     */
    insertVariableAtCursor(input, variable) {
        const start = input.selectionStart;
        const end = input.selectionEnd;
        const text = input.value;

        // Insert variable at cursor position
        const before = text.substring(0, start);
        const after = text.substring(end);
        input.value = before + variable + after;

        // Move cursor after inserted variable
        const newCursorPos = start + variable.length;
        input.setSelectionRange(newCursorPos, newCursorPos);
        input.focus();
    }

    /**
     * Update template preview with real-time validation
     */
    updateTemplatePreview() {
        const template = document.getElementById('default-template').value;
        const preview = document.getElementById('template-preview');

        if (!template) {
            preview.className = 'template-preview';
            preview.innerHTML = '';
            return;
        }

        // Show loading state
        preview.className = 'template-preview template-validating';
        preview.innerHTML = '<span class="validation-spinner">⏳</span> Validating...';

        // Debounce validation API calls (wait 500ms after user stops typing)
        clearTimeout(this.templateValidationTimeout);
        this.templateValidationTimeout = setTimeout(async () => {
            await this.validateTemplateRealtime(template, preview);
        }, 500);
    }

    /**
     * Validate template and update preview with results
     */
    async validateTemplateRealtime(template, previewElement) {
        try {
            // Call API validation endpoint
            const validation = await this.api.validateTemplate(template);

            if (validation.valid) {
                // Show success state with example
                previewElement.className = 'template-preview template-valid';
                previewElement.innerHTML = `
                    <span class="validation-icon">✓</span>
                    <span class="validation-message">Valid template</span>
                    <div class="validation-example">Example: ${validation.example || this.generateExampleFilename(template)}.mp3</div>
                `;
            } else {
                // Show error state with error messages
                previewElement.className = 'template-preview template-invalid';
                const errorList = validation.errors.map(err => `<li>${err}</li>`).join('');
                previewElement.innerHTML = `
                    <span class="validation-icon">✗</span>
                    <span class="validation-message">Invalid template</span>
                    <ul class="validation-errors">${errorList}</ul>
                `;
            }

            // Show warnings if any
            if (validation.warnings && validation.warnings.length > 0) {
                const warningList = validation.warnings.map(warn => `<li>${warn}</li>`).join('');
                previewElement.innerHTML += `<ul class="validation-warnings">${warningList}</ul>`;
            }
        } catch (error) {
            // Show error state if API call fails
            previewElement.className = 'template-preview template-error';
            previewElement.innerHTML = `
                <span class="validation-icon">⚠️</span>
                <span class="validation-message">Could not validate template</span>
                <div class="validation-example">${error.message}</div>
            `;
            console.error('Template validation error:', error);
        }
    }

    /**
     * Generate example filename from template (fallback if API doesn't return one)
     */
    generateExampleFilename(template) {
        return template
            .replace(/{artist}/g, 'Sample Artist')
            .replace(/{title}/g, 'Sample Title')
            .replace(/{album}/g, 'Sample Album')
            .replace(/{year}/g, '2024')
            .replace(/{bpm}/g, '128')
            .replace(/{key}/g, 'Am')
            .replace(/{camelot}/g, '8A')
            .replace(/{label}/g, 'Sample Label')
            .replace(/{track}/g, '01')
            .replace(/{mix}/g, 'Original Mix')
            .replace(/{mix_paren}/g, '(Original Mix)')
            .replace(/{kb}/g, '[Am 128]');
    }

    /**
     * Save settings to API
     */
    async saveSettings() {
        try {
            // Collect form data
            const updates = {
                acoustid_api_key: document.getElementById('acoustid-api-key').value,
                enable_musicbrainz: document.getElementById('enable-musicbrainz').checked,
                auto_detect_bpm: document.getElementById('auto-detect-bpm').checked,
                auto_detect_key: document.getElementById('auto-detect-key').checked,
                use_mb_for_all_fields: document.getElementById('use-mb-for-all-fields').checked,
                verify_mode: document.getElementById('verify-mode').checked,
                default_template: document.getElementById('default-template').value,
                recursive_default: document.getElementById('recursive-default').checked,
                track_number_padding: parseInt(document.getElementById('track-number-padding').value, 10),
                enable_smart_detection: document.getElementById('enable-smart-detection').checked,
                enable_per_album_detection: document.getElementById('enable-per-album-detection').checked, // Task #108
                remember_last_directory: document.getElementById('remember-last-directory').checked, // Task #84
            };

            // Validate template
            if (updates.default_template) {
                const validation = await this.api.validateTemplate(updates.default_template);
                if (!validation.valid) {
                    this.ui.error(`Invalid template: ${validation.errors.join(', ')}`);
                    return;
                }
            }

            // Save to API
            await this.api.updateConfig(updates);

            this.ui.success('Settings saved successfully!');
            this.closeSettings();

        } catch (error) {
            console.error('Error saving settings:', error);
            this.ui.error(`Failed to save settings: ${error.message}`);
        }
    }

    /**
     * Reset settings to defaults
     */
    async resetSettings() {
        if (!confirm('Reset all settings to defaults? This cannot be undone.')) {
            return;
        }

        try {
            // Get default config from API
            const defaults = {
                acoustid_api_key: '8XaBELgH',  // Default public key
                enable_musicbrainz: false,
                auto_detect_bpm: true,
                auto_detect_key: true,
                use_mb_for_all_fields: true,
                verify_mode: false,
                default_template: '{artist} - {title} [{camelot} {bpm}]',
                recursive_default: true,
                track_number_padding: 2,
            };

            // Save defaults
            await this.api.updateConfig(defaults);

            // Reload settings in form
            await this.loadSettings();

            this.ui.success('Settings reset to defaults');

        } catch (error) {
            console.error('Error resetting settings:', error);
            this.ui.error('Failed to reset settings');
        }
    }

    /**
     * Close settings modal
     */
    closeSettings() {
        const modal = document.getElementById('settings-modal');
        modal.classList.add('hidden');
        document.body.style.overflow = '';
    }

    /**
     * Show keyboard shortcuts help modal
     */
    showShortcutsHelp() {
        const modal = document.getElementById('shortcuts-modal');
        if (!modal) {
            console.warn('Shortcuts modal not found in DOM');
            return;
        }

        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';

        // Setup close listeners
        const closeBtn = modal.querySelector('.modal-close');
        const overlay = modal.querySelector('.modal-overlay');
        const closeModalBtn = modal.querySelector('#shortcuts-close-btn');

        const closeHandler = () => this.closeShortcutsHelp();

        if (closeBtn) closeBtn.onclick = closeHandler;
        if (overlay) overlay.onclick = closeHandler;
        if (closeModalBtn) closeModalBtn.onclick = closeHandler;

        // Close on Escape
        modal.onkeydown = (e) => {
            if (e.key === 'Escape') this.closeShortcutsHelp();
        };
    }

    /**
     * Close keyboard shortcuts help modal
     */
    closeShortcutsHelp() {
        const modal = document.getElementById('shortcuts-modal');
        if (modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = '';
        }
    }

    /**
     * Analyze file context and show smart suggestion
     */
    async analyzeAndShowSuggestion() {
        // Check if smart detection is enabled via config
        const config = await this.api.getConfig();
        console.log('Smart detection config check:', { enabled: config.enable_smart_detection });
        if (!config.enable_smart_detection) {
            console.log('Smart detection disabled, skipping');
            return; // Feature disabled
        }

        try {
            // Prepare file data for analysis
            const files = this.currentFiles.map(f => ({
                path: f.path,
                name: f.name,
                size: f.size,
                is_mp3: f.is_mp3,
                metadata: f.metadata || {}
            }));

            console.log('Calling analyze-context API with', files.length, 'files');
            console.log('Sample file metadata:', files[0]?.metadata);

            // Call context analysis endpoint
            const response = await this.api.analyzeContext(files);

            console.log('Analyze-context API response:', response);
            console.log('Has default_suggestion?', !!response.default_suggestion);
            console.log('Per-album mode?', response.per_album_mode);

            // Task #111: Check if per-album mode is active
            if (response.per_album_mode && response.albums && response.albums.length > 1) {
                console.log('Showing per-album banner with', response.albums.length, 'albums');
                this.showPerAlbumBanner(response);
            } else if (response.default_suggestion) {
                console.log('Showing smart suggestion banner (single-banner mode)');
                this.showSmartSuggestion(response);
            } else {
                console.log('No default_suggestion in response - banner not shown');
            }
        } catch (error) {
            console.error('Context analysis failed:', error);
            console.error('Error details:', error.message, error.stack);
            // Don't show error to user - this is a nice-to-have feature
        }
    }

    /**
     * Show smart suggestion banner (Task #128: Auto-apply for high confidence)
     */
    async showSmartSuggestion(contextAnalysis) {
        const banner = document.getElementById('smart-suggestion-banner');
        if (!banner) return;

        const defaultSuggestion = contextAnalysis.default_suggestion;
        if (!defaultSuggestion) return;

        // Task #128: Convert float confidence to string using correct thresholds
        const confidenceFloat = defaultSuggestion.confidence;
        let confidenceLevel = 'low';
        if (confidenceFloat >= 0.9) {
            confidenceLevel = 'high';
        } else if (confidenceFloat >= 0.7) {
            confidenceLevel = 'medium';
        }

        console.log(`[AUTO-APPLY] Confidence: ${confidenceFloat} (${confidenceLevel})`);

        // Task #128: Auto-apply if high confidence (>= 0.9)
        if (confidenceLevel === 'high') {
            console.log('[AUTO-APPLY] High confidence - auto-applying template');

            // Store previous template for undo
            const previousTemplate = this.temporaryTemplate;

            // Auto-apply the suggested template
            await this.applySuggestedTemplate(defaultSuggestion.template);

            // Auto-select all files
            this.toggleSelectAll(true);

            // Show toast notification with undo option
            this.showToast({
                type: 'success',
                title: 'Smart suggestion applied',
                message: `Template: ${defaultSuggestion.template}`,
                actions: [
                    {
                        label: 'Undo',
                        callback: async () => {
                            console.log('[AUTO-APPLY] Undo clicked - reverting template');
                            if (previousTemplate) {
                                this.temporaryTemplate = previousTemplate;
                            } else {
                                this.temporaryTemplate = null;
                            }
                            await this.loadAllPreviews();
                            this.ui.info('Template reverted');
                        },
                        primary: false
                    },
                    {
                        label: 'Dismiss',
                        callback: () => {
                            // Just dismiss
                        },
                        primary: false
                    }
                ],
                duration: 8000 // 8 seconds for undo
            });

            return; // Don't show banner for high confidence
        }

        // Task #128: For medium/low confidence, show banner as usual
        console.log('[AUTO-APPLY] Medium/low confidence - showing banner for user review');

        // Populate banner content
        document.getElementById('suggestion-description').textContent = defaultSuggestion.reason;
        document.getElementById('suggestion-template').textContent = defaultSuggestion.template;

        // Set confidence level class
        banner.className = 'smart-suggestion-banner';
        if (confidenceLevel === 'medium') {
            banner.classList.add('confidence-medium');
            document.getElementById('suggestion-label').textContent = 'Suggested';
            document.getElementById('suggestion-confidence').textContent = 'Medium confidence';
        } else {
            banner.classList.add('confidence-low');
            document.getElementById('suggestion-label').textContent = 'Consider';
            document.getElementById('suggestion-confidence').textContent = 'Low confidence';
        }

        // Show banner
        banner.classList.remove('hidden');

        // Setup event handlers
        document.getElementById('suggestion-use-btn').onclick = async () => {
            await this.applySuggestedTemplate(defaultSuggestion.template);
            this.hideSmartSuggestion();
            // Task #86: Auto-select all files after applying suggested template
            this.toggleSelectAll(true);
        };

        document.getElementById('suggestion-ignore-btn').onclick = async () => {
            this.hideSmartSuggestion();
            // Task #95: Reload previews with user's current template from settings
            await this.loadAllPreviews();
            // Task #86: Auto-select all files (consistent with "Use This" behavior)
            this.toggleSelectAll(true);
        };

        document.getElementById('suggestion-dismiss-btn').onclick = () => {
            this.hideSmartSuggestion();
            // Task #105: Dismiss for current load only (not persistent)
            // Banner will reappear on page refresh or when loading different directory
            this.smartBannerDismissedForCurrentLoad = true;
            console.log('[Task #105] Banner dismissed for current load. Will reappear on refresh or directory change.');
        };
    }

    /**
     * Hide smart suggestion banner
     */
    hideSmartSuggestion() {
        const banner = document.getElementById('smart-suggestion-banner');
        if (banner) {
            banner.classList.add('hidden');
        }
    }

    /**
     * Apply suggested template TEMPORARILY (Task #94 - does NOT save to settings)
     * Template is stored in memory and cleared when loading a new directory
     */
    async applySuggestedTemplate(template) {
        try {
            // Task #94 FIX: Store template in memory only (NOT in settings)
            // This allows Smart Track Detection to be used per-folder without
            // permanently changing the user's default template
            this.temporaryTemplate = template;
            console.log('Applied temporary template (not saved to settings):', template);

            // DON'T update the settings modal - this is temporary!
            // DON'T save to config - this is temporary!

            // Reload previews with new temporary template
            await this.loadAllPreviews();

            this.ui.success(`Temporary template applied: ${template} (not saved to settings)`);
        } catch (error) {
            console.error('Failed to apply suggested template:', error);
            this.ui.error(`Failed to apply template: ${error.message}`);
        }
    }

    /**
     * Cancel preview loading operation (Task #89)
     */
    cancelPreviewLoading() {
        if (this.previewAbortController) {
            console.log('Cancelling preview loading...');
            this.previewAbortController.abort();
            this.previewAbortController = null;
            this.hidePreviewProgress();
            this.ui.info('Preview loading cancelled');
        }
    }

    /**
     * Save last browsed directory to config (Task #84)
     * @param {string} path - Directory path to save
     */
    async saveLastDirectory(path) {
        try {
            await this.api.updateConfig({
                last_directory: path
            });
            console.log(`Saved last directory: ${path}`);
        } catch (error) {
            // Log but don't show to user - non-critical
            console.error('Failed to save last directory:', error);
        }
    }

    // ========================================================================
    // Task #111: Per-Album Smart Detection Functions
    // ========================================================================

    /**
     * Clear per-album state (called when loading new directory)
     */
    clearPerAlbumState() {
        console.log('[PER_ALBUM] Clearing state');
        this.perAlbumState = {
            enabled: false,
            directory: null,
            albums: [],
            locked: false,
            timestamp: null
        };
        this.perAlbumTemplates = null;

        // Hide per-album banner if visible
        const banner = document.getElementById('per-album-banner');
        if (banner) {
            banner.style.display = 'none';
        }
    }

    /**
     * Check if per-album state is valid (not stale)
     */
    isPerAlbumStateValid() {
        if (!this.perAlbumState || !this.perAlbumState.enabled) {
            return false;
        }

        // Check if directory matches
        if (this.perAlbumState.directory !== this.currentPath) {
            console.warn('[PER_ALBUM] State is for different directory');
            return false;
        }

        // Check if state is too old (> 5 minutes)
        if (this.perAlbumState.timestamp) {
            const age = Date.now() - this.perAlbumState.timestamp;
            if (age > 5 * 60 * 1000) {
                console.warn('[PER_ALBUM] State is stale');
                return false;
            }
        }

        return true;
    }

    /**
     * Lock per-album state (prevent changes during operations)
     */
    lockPerAlbumState() {
        this.perAlbumState.locked = true;

        // Disable all checkboxes
        document.querySelectorAll('.album-checkbox').forEach(cb => {
            cb.disabled = true;
        });

        // Disable quick action buttons
        const selectAll = document.getElementById('select-all-albums');
        const deselectAll = document.getElementById('deselect-all-albums');
        const invertSelection = document.getElementById('invert-selection');

        if (selectAll) selectAll.disabled = true;
        if (deselectAll) deselectAll.disabled = true;
        if (invertSelection) invertSelection.disabled = true;
    }

    /**
     * Unlock per-album state (re-enable after operations)
     */
    unlockPerAlbumState() {
        this.perAlbumState.locked = false;

        // Re-enable all checkboxes
        document.querySelectorAll('.album-checkbox').forEach(cb => {
            cb.disabled = false;
        });

        // Re-enable quick action buttons
        const selectAll = document.getElementById('select-all-albums');
        const deselectAll = document.getElementById('deselect-all-albums');
        const invertSelection = document.getElementById('invert-selection');

        if (selectAll) selectAll.disabled = false;
        if (deselectAll) deselectAll.disabled = false;
        if (invertSelection) invertSelection.disabled = false;
    }

    /**
     * Show per-album banner with album selection UI
     */
    showPerAlbumBanner(data) {
        console.log('[PER_ALBUM] Showing banner with', data.albums.length, 'albums');

        // Task #129: Auto-select high-confidence albums
        // Auto-select albums where:
        // - type === 'ALBUM' (complete album with track numbers)
        // - confidence === 'high' (>= 0.9)
        // This reduces friction for batch operations (100+ albums)
        this.perAlbumState = {
            enabled: true,
            directory: this.currentPath,
            albums: data.albums.map(album => ({
                ...album,
                selected: album.detection.type === 'ALBUM' && album.detection.confidence === 'high',
                expanded: false
            })),
            locked: false,
            timestamp: Date.now()
        };

        // Task #129: Count auto-selected albums and show toast
        const autoSelectedCount = this.perAlbumState.albums.filter(a => a.selected).length;
        const totalAlbums = this.perAlbumState.albums.length;

        if (autoSelectedCount > 0) {
            console.log(`[PER_ALBUM] Auto-selected ${autoSelectedCount}/${totalAlbums} high-confidence albums`);

            this.showToast({
                type: 'info',
                title: `${autoSelectedCount} album${autoSelectedCount === 1 ? '' : 's'} auto-selected`,
                message: `High confidence track numbering detected. Review and click "Apply to Selected".`,
                duration: 6000
            });
        }

        // Build HTML
        const banner = document.getElementById('per-album-banner');
        if (!banner) {
            console.error('[PER_ALBUM] Banner element not found');
            return;
        }

        // Show warning if truncated
        let warningHTML = '';
        if (data.warning) {
            warningHTML = `
                <div class="banner-warning">
                    ⚠️ ${data.warning}
                </div>
            `;
        }

        // Build album list
        const albumsHTML = this.perAlbumState.albums.map((album, index) => {
            const detectionIcon = this.getDetectionIcon(album.detection.type);
            const detectionClass = this.getDetectionClass(album.detection.type);

            return `
                <div class="album-item ${album.selected ? 'selected' : ''}" data-album-index="${index}">
                    <div class="album-item-header">
                        <label class="album-checkbox-label">
                            <input type="checkbox"
                                   class="album-checkbox"
                                   ${album.selected ? 'checked' : ''}
                                   data-album-index="${index}">
                            <span class="album-detection-icon">${detectionIcon}</span>
                            <span class="album-name">Album: ${this.escapeHtml(album.album_name)}</span>
                        </label>
                        <div class="album-header-info">
                            <span class="album-file-count">${album.file_count} files</span>
                            <button class="album-expand-btn"
                                    data-album-index="${index}"
                                    aria-label="Expand album details"
                                    aria-expanded="false">
                                <span class="expand-icon">▶</span>
                            </button>
                        </div>
                    </div>
                    <div class="album-item-details hidden">
                        <div class="album-path">📁 ${this.escapeHtml(album.path)}</div>
                        <div class="album-detection">
                            <span class="detection-badge ${detectionClass}">
                                ${detectionIcon} ${album.detection.type} detected (${album.detection.confidence} confidence)
                            </span>
                        </div>
                        <div class="album-template">
                            <strong>Template:</strong> ${album.detection.suggested_template ?
                                `<code>${this.escapeHtml(album.detection.suggested_template)}</code>` :
                                'Not recommended'}
                        </div>
                        <div class="album-reason">
                            <strong>Reason:</strong> ${this.escapeHtml(album.detection.reason || 'N/A')}
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        banner.innerHTML = `
            <div class="banner-header">
                <div class="banner-title">
                    <span class="banner-icon">🎵</span>
                    <span class="banner-text">Smart Track Detection - Multiple Albums Detected</span>
                </div>
                <button class="banner-close" onclick="app.dismissPerAlbumBanner()" aria-label="Dismiss">×</button>
            </div>
            <div class="banner-content">
                ${warningHTML}
                <p class="banner-description">
                    Select which albums should use smart track detection:
                </p>
                <div class="banner-actions-top">
                    <button class="btn-secondary btn-sm" id="select-all-albums">Select All</button>
                    <button class="btn-secondary btn-sm" id="deselect-all-albums">Deselect All</button>
                    <button class="btn-secondary btn-sm" id="invert-selection">Invert Selection</button>
                    <button class="btn-primary" id="apply-per-album-selection">Apply to Selected</button>
                </div>
                <div class="album-list">
                    ${albumsHTML}
                </div>
                <div class="banner-info">
                    <span class="info-icon">ℹ️</span>
                    Checked albums will use smart template. Unchecked albums will use your global template from settings.
                </div>
            </div>
        `;

        banner.style.display = 'block';

        // Setup event listeners
        this.setupPerAlbumListeners();
    }

    /**
     * Setup event listeners for per-album banner
     */
    setupPerAlbumListeners() {
        // Album checkbox changes
        document.querySelectorAll('.album-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const index = parseInt(e.target.dataset.albumIndex);
                this.onAlbumCheckboxChange(index, e.target.checked);
            });
        });

        // Expand/collapse buttons
        document.querySelectorAll('.album-expand-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const index = parseInt(e.currentTarget.dataset.albumIndex);
                this.toggleAlbumExpanded(index);
            });
        });

        // Quick action buttons
        const selectAll = document.getElementById('select-all-albums');
        const deselectAll = document.getElementById('deselect-all-albums');
        const invertSelection = document.getElementById('invert-selection');
        const applyButton = document.getElementById('apply-per-album-selection');

        if (selectAll) {
            selectAll.addEventListener('click', () => this.selectAllAlbums());
        }

        if (deselectAll) {
            deselectAll.addEventListener('click', () => this.deselectAllAlbums());
        }

        if (invertSelection) {
            invertSelection.addEventListener('click', () => this.invertAlbumSelection());
        }

        if (applyButton) {
            applyButton.addEventListener('click', () => this.applyPerAlbumSelection());
        }
    }

    /**
     * Handle album checkbox change
     */
    onAlbumCheckboxChange(index, checked) {
        if (this.perAlbumState.locked) {
            console.log('[PER_ALBUM] State locked, ignoring checkbox change');
            return;
        }

        console.log(`[PER_ALBUM] Album ${index} ${checked ? 'selected' : 'unselected'}`);

        // Update state
        this.perAlbumState.albums[index].selected = checked;

        // Update UI
        const albumItem = document.querySelector(`.album-item[data-album-index="${index}"]`);
        if (albumItem) {
            albumItem.classList.toggle('selected', checked);
        }
    }

    /**
     * Toggle album details expanded/collapsed
     */
    toggleAlbumExpanded(index) {
        const album = this.perAlbumState.albums[index];
        album.expanded = !album.expanded;

        const albumItem = document.querySelector(`.album-item[data-album-index="${index}"]`);
        if (!albumItem) return;

        const details = albumItem.querySelector('.album-item-details');
        const expandBtn = albumItem.querySelector('.album-expand-btn');

        if (details) {
            details.classList.toggle('hidden', !album.expanded);
        }

        if (expandBtn) {
            expandBtn.setAttribute('aria-expanded', album.expanded);
        }
    }

    /**
     * Select all albums
     */
    selectAllAlbums() {
        console.log('[PER_ALBUM] Selecting all albums');

        this.perAlbumState.albums.forEach((album, index) => {
            album.selected = true;
            const checkbox = document.querySelector(`.album-checkbox[data-album-index="${index}"]`);
            if (checkbox) checkbox.checked = true;

            const albumItem = document.querySelector(`.album-item[data-album-index="${index}"]`);
            if (albumItem) albumItem.classList.add('selected');
        });
    }

    /**
     * Deselect all albums
     */
    deselectAllAlbums() {
        console.log('[PER_ALBUM] Deselecting all albums');

        this.perAlbumState.albums.forEach((album, index) => {
            album.selected = false;
            const checkbox = document.querySelector(`.album-checkbox[data-album-index="${index}"]`);
            if (checkbox) checkbox.checked = false;

            const albumItem = document.querySelector(`.album-item[data-album-index="${index}"]`);
            if (albumItem) albumItem.classList.remove('selected');
        });
    }

    /**
     * Invert album selection
     */
    invertAlbumSelection() {
        console.log('[PER_ALBUM] Inverting selection');

        this.perAlbumState.albums.forEach((album, index) => {
            album.selected = !album.selected;
            const checkbox = document.querySelector(`.album-checkbox[data-album-index="${index}"]`);
            if (checkbox) checkbox.checked = album.selected;

            const albumItem = document.querySelector(`.album-item[data-album-index="${index}"]`);
            if (albumItem) albumItem.classList.toggle('selected', album.selected);
        });
    }

    /**
     * Apply per-album template selections
     */
    async applyPerAlbumSelection() {
        if (!this.isPerAlbumStateValid()) {
            this.ui.error('Per-album state is invalid. Please reload directory.');
            return;
        }

        console.log('[PER_ALBUM] Applying selections');

        // Check if any albums selected
        const selectedCount = this.perAlbumState.albums.filter(a => a.selected).length;
        if (selectedCount === 0) {
            this.ui.warning('Please select at least one album');
            return;
        }

        try {
            // Lock state during preview generation
            this.lockPerAlbumState();

            // Build per-album template map
            this.perAlbumTemplates = {};
            this.perAlbumState.albums.forEach(album => {
                if (album.selected && album.detection.suggested_template) {
                    this.perAlbumTemplates[album.path] = album.detection.suggested_template;
                }
            });

            // Clear temporary template (per-album takes precedence)
            this.temporaryTemplate = null;

            console.log('[PER_ALBUM] Template map:', this.perAlbumTemplates);

            // Reload previews with per-album templates
            await this.loadAllPreviews();

            this.ui.success(`Previews updated for ${selectedCount} selected albums`);

        } catch (error) {
            console.error('[PER_ALBUM] Apply failed:', error);
            this.ui.error(`Failed to apply templates: ${error.message}`);
        } finally {
            // Unlock state
            this.unlockPerAlbumState();
        }
    }

    /**
     * Dismiss per-album banner
     */
    dismissPerAlbumBanner() {
        console.log('[PER_ALBUM] Dismissing banner');

        const banner = document.getElementById('per-album-banner');
        if (banner) {
            banner.style.display = 'none';
        }

        // Clear state
        this.clearPerAlbumState();
    }

    /**
     * Get detection icon for album type
     */
    getDetectionIcon(type) {
        const icons = {
            'ALBUM': '✓',
            'PARTIAL_ALBUM': '~',
            'INCOMPLETE_ALBUM': '⚠',
            'SINGLES': '✗',
            'UNKNOWN': '?'
        };
        return icons[type] || '?';
    }

    /**
     * Get CSS class for detection type
     */
    getDetectionClass(type) {
        const classes = {
            'ALBUM': 'detection-album',
            'PARTIAL_ALBUM': 'detection-partial',
            'INCOMPLETE_ALBUM': 'detection-partial',
            'SINGLES': 'detection-singles',
            'UNKNOWN': 'detection-unknown'
        };
        return classes[type] || 'detection-unknown';
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Get album path for a file (for per-album template lookup)
     */
    getAlbumPathForFile(filePath) {
        if (!this.perAlbumState || !this.perAlbumState.albums) {
            return null;
        }

        // Find album that contains this file
        for (const album of this.perAlbumState.albums) {
            if (album.files && album.files.includes(filePath)) {
                return album.path;
            }
        }

        return null;
    }

    /**
     * Get template for a specific file (per-album, temporary, or settings)
     */
    getTemplateForFile(filePath) {
        // 1. Check per-album templates first
        if (this.perAlbumTemplates) {
            const albumPath = this.getAlbumPathForFile(filePath);
            if (albumPath && this.perAlbumTemplates[albumPath]) {
                return this.perAlbumTemplates[albumPath];
            }
        }

        // 2. Check temporary template
        if (this.temporaryTemplate) {
            return this.temporaryTemplate;
        }

        // 3. Fall back to settings template
        const templateInput = document.getElementById('template-input');
        return templateInput ? templateInput.value : '';
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
