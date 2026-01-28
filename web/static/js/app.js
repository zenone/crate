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
    configSection: document.getElementById('config-section'),
    resultsSection: document.getElementById('results-section'),
    templateInput: document.getElementById('template-input'),
    previewBtn: document.getElementById('preview-btn'),
    renameBtn: document.getElementById('rename-btn'),
    resultsStats: document.getElementById('results-stats'),
    resultsList: document.getElementById('results-list'),
    newBatchBtn: document.getElementById('new-batch-btn'),
    themeToggle: document.getElementById('theme-toggle'),
    loading: document.getElementById('loading'),
    loadingText: document.getElementById('loading-text'),
    toast: document.getElementById('toast'),
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
    elements.configSection.classList.add('hidden');
    elements.resultsSection.classList.add('hidden');
    section.classList.remove('hidden');
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
}

function resetApp() {
    state.sessionId = null;
    state.files = [];
    state.template = '';
    elements.fileList.innerHTML = '';
    elements.fileList.classList.add('hidden');
    elements.templateInput.value = '';
    elements.renameBtn.disabled = true;
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
