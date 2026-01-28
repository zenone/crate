/**
 * DJ MP3 Renamer - Frontend Application
 * Modern vanilla JavaScript with async/await
 */

// ==================== State Management ====================

const state = {
    sessionId: null,
    files: [],
    template: '',
    isDryRun: true,
    theme: null,
};

// ==================== DOM Elements ====================

const elements = {
    uploadZone: document.getElementById('upload-zone'),
    fileInput: document.getElementById('file-input'),
    browseBtn: document.getElementById('browse-btn'),
    fileList: document.getElementById('file-list'),
    uploadSection: document.getElementById('upload-section'),
    localSection: document.getElementById('local-section'),
    configSection: document.getElementById('config-section'),
    resultsSection: document.getElementById('results-section'),
    templateInput: document.getElementById('template-input'),
    previewBtn: document.getElementById('preview-btn'),
    renameBtn: document.getElementById('rename-btn'),
    renameFilesBtn: document.getElementById('rename-files-btn'),
    downloadBtn: document.getElementById('download-btn'),
    resultsStats: document.getElementById('results-stats'),
    resultsList: document.getElementById('results-list'),
    newBatchBtn: document.getElementById('new-batch-btn'),
    themeToggle: document.getElementById('theme-toggle'),
    loading: document.getElementById('loading'),
    loadingText: document.getElementById('loading-text'),
    toast: document.getElementById('toast'),
    modeUploadBtn: document.getElementById('mode-upload'),
    modeLocalBtn: document.getElementById('mode-local'),
    localPathInput: document.getElementById('local-path-input'),
    localRecursive: document.getElementById('local-recursive'),
    browseFolderBtn: document.getElementById('browse-folder-btn'),
    processLocalBtn: document.getElementById('process-local-btn'),
};

// ==================== Theme Management ====================

function initTheme() {
    // Check localStorage or system preference
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    state.theme = savedTheme || (systemPrefersDark ? 'dark' : 'light');
    applyTheme(state.theme);

    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
            applyTheme(e.matches ? 'dark' : 'light');
        }
    });
}

function applyTheme(theme) {
    state.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
}

function toggleTheme() {
    const newTheme = state.theme === 'light' ? 'dark' : 'light';
    applyTheme(newTheme);
}

// ==================== UI Helpers ====================

function showLoading(text = 'Processing...') {
    elements.loadingText.textContent = text;
    elements.loading.classList.remove('hidden');
}

function hideLoading() {
    elements.loading.classList.add('hidden');
}

function showToast(message, type = 'success') {
    elements.toast.textContent = message;
    elements.toast.className = `toast ${type}`;
    elements.toast.classList.remove('hidden');

    setTimeout(() => {
        elements.toast.classList.add('hidden');
    }, 3000);
}

function showSection(section) {
    elements.uploadSection.classList.add('hidden');
    elements.localSection.classList.add('hidden');
    elements.configSection.classList.add('hidden');
    elements.resultsSection.classList.add('hidden');
    section.classList.remove('hidden');
}

// ==================== Mode Switching ====================

function switchMode(mode) {
    // Update button states
    elements.modeUploadBtn.classList.remove('active');
    elements.modeLocalBtn.classList.remove('active');

    if (mode === 'upload') {
        elements.modeUploadBtn.classList.add('active');
        showSection(elements.uploadSection);
    } else {
        elements.modeLocalBtn.classList.add('active');
        showSection(elements.localSection);
        // Auto-focus the path input when switching to local mode
        setTimeout(() => elements.localPathInput.focus(), 100);
    }

    // Reset state
    resetApp();
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// ==================== File Upload ====================

function handleFiles(files) {
    const mp3Files = Array.from(files).filter(file =>
        file.name.toLowerCase().endsWith('.mp3')
    );

    if (mp3Files.length === 0) {
        showToast('Please select MP3 files', 'error');
        return;
    }

    uploadFiles(mp3Files);
}

async function uploadFiles(files) {
    showLoading('Uploading files...');

    const formData = new FormData();
    files.forEach(file => {
        formData.append('files', file);
    });

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error('Upload failed');
        }

        const data = await response.json();
        state.sessionId = data.session_id;
        state.files = data.files;

        displayFileList();
        loadDefaultTemplate();
        showSection(elements.configSection);
        showToast(`Uploaded ${data.count} file(s) successfully`);
    } catch (error) {
        console.error('Upload error:', error);
        showToast('Upload failed. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

function displayFileList() {
    if (state.files.length === 0) {
        elements.fileList.classList.add('hidden');
        return;
    }

    elements.fileList.classList.remove('hidden');
    elements.fileList.innerHTML = `
        <h3 style="margin-bottom: 1rem; color: var(--text-primary);">
            Uploaded Files (${state.files.length})
        </h3>
        ${state.files.map(file => `
            <div class="file-item">
                <div class="file-info">
                    <svg class="file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M9 18V5l12-2v13"></path>
                        <circle cx="6" cy="18" r="3"></circle>
                        <circle cx="18" cy="16" r="3"></circle>
                    </svg>
                    <span class="file-name">${file.name}</span>
                </div>
                <span class="file-size">${formatFileSize(file.size)}</span>
            </div>
        `).join('')}
    `;
}

async function loadDefaultTemplate() {
    try {
        const response = await fetch('/api/templates');
        const data = await response.json();
        elements.templateInput.value = data.default;
        state.template = data.default;
    } catch (error) {
        console.error('Failed to load template:', error);
    }
}

// ==================== Rename Operations ====================

async function previewRename() {
    const template = elements.templateInput.value.trim();
    if (!template) {
        showToast('Please enter a template', 'error');
        return;
    }

    showLoading('Generating preview...');

    try {
        const response = await fetch('/api/rename', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: state.sessionId,
                template: template,
                dry_run: true,
                recursive: false,
            }),
        });

        if (!response.ok) {
            throw new Error('Preview failed');
        }

        const data = await response.json();
        displayResults(data, true);
        showSection(elements.resultsSection);
        elements.renameBtn.disabled = false;
        showToast('Preview generated successfully');
    } catch (error) {
        console.error('Preview error:', error);
        showToast('Preview failed. Please check your template.', 'error');
    } finally {
        hideLoading();
    }
}

async function executeRename() {
    const confirmed = confirm(
        'This will rename your files. Are you sure you want to continue?'
    );

    if (!confirmed) return;

    const template = elements.templateInput.value.trim();
    showLoading('Renaming files...');

    try {
        const response = await fetch('/api/rename', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: state.sessionId,
                template: template,
                dry_run: false,
                recursive: false,
            }),
        });

        if (!response.ok) {
            throw new Error('Rename failed');
        }

        const data = await response.json();
        displayResults(data, false);
        showSection(elements.resultsSection);
        showToast(`Successfully renamed ${data.renamed} file(s)`);
    } catch (error) {
        console.error('Rename error:', error);
        showToast('Rename failed. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

function displayResults(data, isPreview) {
    // Stats
    elements.resultsStats.innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${data.total}</div>
            <div class="stat-label">Total</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color: var(--success)">${data.renamed}</div>
            <div class="stat-label">${isPreview ? 'To Rename' : 'Renamed'}</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color: var(--warning)">${data.skipped}</div>
            <div class="stat-label">Skipped</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color: var(--error)">${data.errors}</div>
            <div class="stat-label">Errors</div>
        </div>
    `;

    // Results list
    elements.resultsList.innerHTML = data.results.map(result => {
        const statusClass = result.status === 'renamed' ? 'success' :
                          result.status === 'skipped' ? 'skipped' : 'error';

        return `
            <div class="result-item ${statusClass}">
                <div class="result-src">${result.src}</div>
                ${result.dst ? `
                    <div class="result-arrow">↓</div>
                    <div class="result-dst">${result.dst}</div>
                ` : `
                    <div style="color: var(--text-secondary); margin-top: 0.5rem; font-size: 0.875rem;">
                        ${result.message || 'Skipped'}
                    </div>
                `}
            </div>
        `;
    }).join('');

    // Button visibility logic
    if (isPreview) {
        // After preview: show "Rename Files" button, hide "Download" button
        elements.renameFilesBtn.classList.remove('hidden');
        elements.downloadBtn.classList.add('hidden');
    } else {
        // After actual rename: hide "Rename Files" button, show "Download" button if files were renamed
        elements.renameFilesBtn.classList.add('hidden');
        if (data.renamed > 0) {
            elements.downloadBtn.classList.remove('hidden');
        } else {
            elements.downloadBtn.classList.add('hidden');
        }
    }
}

async function downloadFiles() {
    if (!state.sessionId) {
        showToast('No session found', 'error');
        return;
    }

    showLoading('Preparing download...');

    try {
        const response = await fetch(`/api/download/${state.sessionId}`, {
            method: 'POST',
        });

        if (!response.ok) {
            throw new Error('Download failed');
        }

        // Create blob from response
        const blob = await response.blob();

        // Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `renamed-files-${new Date().toISOString().slice(0, 10)}.zip`;
        document.body.appendChild(a);
        a.click();

        // Cleanup
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        showToast('Download started');
    } catch (error) {
        console.error('Download error:', error);
        showToast('Download failed. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

// ==================== Local Directory Processing ====================

async function processLocalDirectory(dryRun = true) {
    const path = elements.localPathInput.value.trim();

    if (!path) {
        showToast('Please enter a directory path', 'error');
        return;
    }

    const template = elements.templateInput.value.trim() || '{artist} - {title}{mix_paren}{kb}';
    const recursive = elements.localRecursive.checked;

    showLoading(dryRun ? 'Generating preview...' : 'Renaming files...');

    try {
        const response = await fetch('/api/rename-local', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                path: path,
                template: template,
                dry_run: dryRun,
                recursive: recursive,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Operation failed');
        }

        const data = await response.json();

        // Show config section with template if not already shown
        if (elements.configSection.classList.contains('hidden')) {
            elements.templateInput.value = template;
            showSection(elements.configSection);
        }

        // Display results
        displayResults(data, dryRun);
        showSection(elements.resultsSection);

        if (dryRun) {
            showToast(`Preview: ${data.total} file(s) found`);
        } else {
            showToast(`Successfully renamed ${data.renamed} file(s)`);
        }
    } catch (error) {
        console.error('Process error:', error);
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function previewLocalDirectory() {
    await processLocalDirectory(true);
}

async function renameLocalDirectory() {
    const confirmed = confirm(
        'This will rename files in your local directory. Are you sure?'
    );

    if (!confirmed) return;

    await processLocalDirectory(false);
}

function resetApp() {
    state.sessionId = null;
    state.files = [];
    state.template = '';
    elements.fileList.innerHTML = '';
    elements.fileList.classList.add('hidden');
    elements.templateInput.value = '';
    elements.renameBtn.disabled = true;
    elements.renameFilesBtn.classList.add('hidden');
    elements.downloadBtn.classList.add('hidden');
    showSection(elements.uploadSection);
}

// ==================== Event Listeners ====================

// Theme toggle
elements.themeToggle.addEventListener('click', toggleTheme);

// File input
elements.browseBtn.addEventListener('click', () => {
    elements.fileInput.click();
});

elements.fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFiles(e.target.files);
    }
});

// Drag and drop
elements.uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    elements.uploadZone.classList.add('drag-over');
});

elements.uploadZone.addEventListener('dragleave', () => {
    elements.uploadZone.classList.remove('drag-over');
});

elements.uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    elements.uploadZone.classList.remove('drag-over');
    handleFiles(e.dataTransfer.files);
});

// Click to upload
elements.uploadZone.addEventListener('click', (e) => {
    if (e.target !== elements.browseBtn) {
        elements.fileInput.click();
    }
});

// Preview and rename buttons
elements.previewBtn.addEventListener('click', previewRename);
elements.renameBtn.addEventListener('click', executeRename);
elements.renameFilesBtn.addEventListener('click', () => {
    // Check if we're in local mode or upload mode
    if (elements.localPathInput.value.trim()) {
        renameLocalDirectory();
    } else {
        executeRename();
    }
});

// Download button
elements.downloadBtn.addEventListener('click', downloadFiles);

// Mode switching
elements.modeUploadBtn.addEventListener('click', () => switchMode('upload'));
elements.modeLocalBtn.addEventListener('click', () => switchMode('local'));

// Local directory processing
elements.processLocalBtn.addEventListener('click', previewLocalDirectory);

// Quick path buttons
document.querySelectorAll('.btn-quick-path').forEach(btn => {
    btn.addEventListener('click', () => {
        const path = btn.dataset.path;
        elements.localPathInput.value = path;
        elements.localPathInput.focus();
    });
});

// New batch button
elements.newBatchBtn.addEventListener('click', () => {
    // Cleanup session
    if (state.sessionId) {
        fetch(`/api/session/${state.sessionId}`, {
            method: 'DELETE',
        }).catch(err => console.error('Cleanup error:', err));
    }
    resetApp();
});

// ==================== Initialization ====================

function init() {
    initTheme();
    showSection(elements.uploadSection);
    console.log('DJ MP3 Renamer initialized');
}

// Start the app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
