# DJ MP3 Renamer - Coding Standards

## Code Style & Conventions

This document defines coding standards for maintaining consistent, high-quality code across the project.

---

## Python Code Standards

### Style Guide
Follow **PEP 8** with these specific guidelines:

**Line Length**: 120 characters max (more readable on modern displays)

**Imports**:
```python
# Standard library
import os
import sys
from pathlib import Path
from typing import Optional, List

# Third-party
import click
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Local
from ..core.io import read_mp3_metadata
from .models import RenameRequest, RenameResult
```

**Naming**:
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

**Type Hints**: Always use type hints for function parameters and return values
```python
def rename_file(src: Path, dst: Path, dry_run: bool = False) -> bool:
    """Rename file with optional dry-run mode."""
    ...
```

**Docstrings**: Use Google-style docstrings
```python
def validate_template(template: str) -> TemplateValidation:
    """
    Validate filename template.

    Checks template for invalid characters, unknown variables, and
    generates example output with sample data.

    Args:
        template: Template string to validate

    Returns:
        TemplateValidation with errors, warnings, and example

    Examples:
        >>> result = validate_template("{artist} - {title}")
        >>> print(result.valid)
        True
    """
```

### Data Classes vs. Pydantic Models

**Use `@dataclass` for**:
- Internal API models (RenameRequest, RenameResult)
- Models that don't need validation
- Immutable models (`frozen=True`)

**Use Pydantic `BaseModel` for**:
- Web API request/response models
- Models that need validation
- Models with computed fields

**Example**:
```python
# Internal API - dataclass
from dataclasses import dataclass

@dataclass(frozen=True)
class RenameRequest:
    path: Path
    recursive: bool = False
    dry_run: bool = False

# Web API - Pydantic
from pydantic import BaseModel

class DirectoryRequest(BaseModel):
    path: str  # Will be validated as string, converted to Path in handler
```

### Error Handling

**Always catch specific exceptions**:
```python
# ❌ Bad
try:
    do_something()
except Exception:
    pass

# ✅ Good
try:
    file_path.read_text()
except FileNotFoundError:
    logger.error(f"File not found: {file_path}")
    return None
except PermissionError:
    logger.error(f"Permission denied: {file_path}")
    return None
```

**Use context managers** for resource management:
```python
# ✅ Good
with open(file_path) as f:
    content = f.read()

# ✅ Better
from pathlib import Path
content = Path(file_path).read_text()
```

---

## JavaScript Code Standards

### Style Guide

**Naming**:
- Variables/functions: `camelCase`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leadingUnderscore`

**Classes**: Use ES6 class syntax
```javascript
class RenamerAPI {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
    }

    async health() {
        return this._fetch('/api/health');
    }

    async _fetch(endpoint, options = {}) {
        // Private method
    }
}
```

**Async/Await**: Prefer `async/await` over `.then()` chains
```javascript
// ❌ Bad
function loadFiles() {
    api.listDirectory(path)
        .then(result => {
            this.updateFiles(result);
        })
        .catch(error => {
            console.error(error);
        });
}

// ✅ Good
async loadFiles() {
    try {
        const result = await api.listDirectory(path);
        this.updateFiles(result);
    } catch (error) {
        console.error(error);
        this.ui.error(`Failed to load files: ${error.message}`);
    }
}
```

**Template Literals**: Use for string interpolation
```javascript
// ❌ Bad
const message = 'Loaded ' + count + ' files';

// ✅ Good
const message = `Loaded ${count} files`;
```

**Destructuring**: Use for cleaner code
```javascript
// ✅ Good
const { artist, title, bpm, key } = metadata;
const { path, files, total } = result;
```

**Arrow Functions**: Use for callbacks and short functions
```javascript
// ✅ Good
const mp3s = files.filter(f => f.is_mp3);
const names = files.map(f => f.name);
checkboxes.forEach(cb => cb.checked = true);
```

**JSDoc Comments**: Document public methods
```javascript
/**
 * Load directory contents
 *
 * @param {string} path - Directory path
 * @returns {Promise<void>}
 */
async loadDirectory(path) {
    // ...
}
```

### DOM Manipulation

**Cache DOM queries**:
```javascript
// ❌ Bad - queries DOM multiple times
function updateUI() {
    document.getElementById('count').textContent = '5';
    document.getElementById('count').classList.add('active');
    document.getElementById('count').style.color = 'red';
}

// ✅ Good - query once
function updateUI() {
    const countEl = document.getElementById('count');
    countEl.textContent = '5';
    countEl.classList.add('active');
    countEl.style.color = 'red';
}
```

**Use data attributes** for storing state:
```javascript
// ✅ Good
<div class="file-row" data-path="/music/track.mp3" data-selected="true">

// JavaScript
const path = element.dataset.path;
const selected = element.dataset.selected === 'true';
```

---

## CSS Code Standards

### Organization

**Order of sections**:
1. CSS Variables (`:root`)
2. Reset & Base styles
3. Layout (grid, flexbox)
4. Components (buttons, cards, modals)
5. Utilities (helpers, animations)
6. Media queries

**Example**:
```css
/* 1. CSS Variables */
:root {
    --accent-primary: #6366f1;
}

/* 2. Reset & Base */
* { margin: 0; padding: 0; }

/* 3. Layout */
.container { display: grid; }

/* 4. Components */
.btn { padding: 1rem; }

/* 5. Utilities */
.hidden { display: none; }

/* 6. Media Queries */
@media (max-width: 768px) { }
```

### Naming Conventions

**BEM-like naming** (Block, Element, Modifier):
```css
/* Block */
.preview-modal { }

/* Element */
.preview-modal__header { }
.preview-modal__body { }

/* Modifier */
.preview-modal--large { }
.preview-modal__button--primary { }
```

**However, we use simpler naming in this project**:
```css
/* Component */
.preview-modal { }

/* Child elements */
.preview-modal .modal-header { }
.preview-modal .modal-body { }

/* States/variants */
.preview-modal.large { }
.modal-button.primary { }
```

### CSS Variables

**Use CSS variables** for consistency:
```css
:root {
    /* Colors */
    --bg-primary: #0f0f1e;
    --text-primary: #ffffff;
    --accent-primary: #6366f1;

    /* Spacing */
    --spacing-sm: 1rem;
    --spacing-md: 1.5rem;

    /* Border Radius */
    --radius-md: 1rem;
}

/* Usage */
.card {
    background: var(--bg-primary);
    padding: var(--spacing-md);
    border-radius: var(--radius-md);
}
```

### Responsive Design

**Mobile-first approach**:
```css
/* Base styles (mobile) */
.container {
    padding: 1rem;
}

/* Tablet and up */
@media (min-width: 768px) {
    .container {
        padding: 2rem;
    }
}

/* Desktop and up */
@media (min-width: 1024px) {
    .container {
        padding: 3rem;
    }
}
```

---

## HTML Code Standards

### Semantic HTML

**Use semantic tags**:
```html
<!-- ✅ Good -->
<header>
    <nav>
        <ul>
            <li><a href="#home">Home</a></li>
        </ul>
    </nav>
</header>

<main>
    <section>
        <article>
            <h2>Title</h2>
            <p>Content</p>
        </article>
    </section>
</main>

<footer>
    <p>&copy; 2024</p>
</footer>
```

### Accessibility

**Always include**:
- `alt` text for images
- `aria-label` for icon buttons
- `aria-labelledby` and `aria-describedby` for complex components
- `role` attributes for ARIA landmarks

**Example**:
```html
<button
    id="close-btn"
    class="modal-close"
    aria-label="Close dialog"
    title="Close"
>
    ✕
</button>

<div
    id="preview-modal"
    class="modal"
    role="dialog"
    aria-labelledby="preview-modal-title"
    aria-modal="true"
>
    <h2 id="preview-modal-title">Preview Rename</h2>
</div>
```

### Form Inputs

**Always label inputs**:
```html
<!-- ✅ Good -->
<div class="form-group">
    <label for="directory-path">Directory Path</label>
    <input
        type="text"
        id="directory-path"
        name="directory-path"
        placeholder="/path/to/music"
        aria-label="Directory path"
        required
    >
</div>
```

---

## API Design Standards

### REST Endpoints

**Follow RESTful conventions**:
```
GET    /api/resource         - List resources
GET    /api/resource/:id     - Get single resource
POST   /api/resource         - Create resource
PUT    /api/resource/:id     - Update resource (full)
PATCH  /api/resource/:id     - Update resource (partial)
DELETE /api/resource/:id     - Delete resource
```

**Our endpoints**:
```
GET    /api/health           - Health check
POST   /api/directory/list   - List directory (POST because body has options)
POST   /api/directory/browse - Browse directory tree
POST   /api/file/metadata    - Get file metadata
POST   /api/rename/preview   - Preview rename
POST   /api/rename/execute   - Execute rename
GET    /api/operation/:id    - Get operation status
POST   /api/operation/:id/cancel - Cancel operation
GET    /api/config           - Get config
POST   /api/config/update    - Update config
```

### Request/Response Models

**Always validate with Pydantic**:
```python
from pydantic import BaseModel
from typing import Optional, List

class DirectoryRequest(BaseModel):
    path: str

class FileInfo(BaseModel):
    path: str
    name: str
    size: int
    is_mp3: bool
    metadata: Optional[dict] = None

class DirectoryResponse(BaseModel):
    path: str
    files: List[FileInfo]
    total_files: int
    mp3_count: int
```

### Error Responses

**Consistent error format**:
```python
from fastapi import HTTPException

# ✅ Good
raise HTTPException(
    status_code=404,
    detail="Directory not found: /invalid/path"
)

# ✅ Good
raise HTTPException(
    status_code=400,
    detail="Path is not a directory: /file.txt"
)
```

**HTTP Status Codes**:
- `200 OK` - Success
- `400 Bad Request` - Invalid input
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

---

## Testing Standards

### Test Organization

**File structure**:
```
tests/
├── unit/                    # Unit tests
│   ├── test_io.py
│   ├── test_template.py
│   └── test_api.py
├── integration/             # Integration tests
│   ├── test_web_api.py
│   └── test_rename_flow.py
└── fixtures/                # Test data
    ├── sample.mp3
    └── test_config.yaml
```

### Test Naming

**Pattern**: `test_<function>_<scenario>_<expected_result>`

**Examples**:
```python
def test_validate_template_with_valid_template_returns_valid():
    """Valid template should return valid=True"""

def test_validate_template_with_empty_template_returns_error():
    """Empty template should return error"""

def test_rename_file_with_duplicate_name_adds_counter():
    """Duplicate filename should add (1) counter"""
```

### Test Structure

**Arrange-Act-Assert pattern**:
```python
def test_read_mp3_metadata_returns_tags():
    # Arrange
    file_path = Path("tests/fixtures/sample.mp3")
    logger = logging.getLogger("test")

    # Act
    metadata, error = read_mp3_metadata(file_path, logger)

    # Assert
    assert error is None
    assert metadata is not None
    assert "artist" in metadata
    assert "title" in metadata
```

### Fixtures

**Use pytest fixtures** for common setup:
```python
import pytest
from pathlib import Path

@pytest.fixture
def sample_mp3():
    """Provide path to sample MP3 file"""
    return Path("tests/fixtures/sample.mp3")

@pytest.fixture
def temp_dir(tmp_path):
    """Provide temporary directory"""
    return tmp_path

def test_rename_file(sample_mp3, temp_dir):
    # Use fixtures
    dst = temp_dir / "renamed.mp3"
    os.rename(sample_mp3, dst)
    assert dst.exists()
```

---

## Git & Version Control

### Branch Strategy

**Main branches**:
- `main` - Production-ready code
- `develop` - Development branch (if needed)

**Feature branches**:
- `feat/preview-modal` - New features
- `fix/port-conflict` - Bug fixes
- `refactor/api-layer` - Refactoring
- `docs/readme-update` - Documentation

### Commit Messages

**Format**:
```
<type>: <subject>

<body>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Types**:
- `feat` - New feature
- `fix` - Bug fix
- `refactor` - Code restructuring
- `docs` - Documentation
- `test` - Tests
- `chore` - Maintenance
- `style` - Code style

**Subject**:
- Start with lowercase
- No period at end
- Max 70 characters
- Imperative mood ("add" not "added")

**Body**:
- Explain WHAT and WHY (not HOW)
- Wrap at 72 characters
- Bullet points OK

**Example**:
```
feat: Add preview modal with metadata source indicators

- Created preview modal UI with statistics display
- Added metadata source badges (ID3/MusicBrainz/AI)
- Implemented selective file rename with checkboxes
- Added progress overlay with terminal-style output

This enables users to review changes before executing
destructive rename operations.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### What to Commit

**Always commit**:
- Source code changes
- Configuration files
- Documentation
- Test files

**Never commit**:
- `__pycache__/` directories
- `.pyc` files
- `.venv/` virtual environment
- `.env` environment variables
- `.DS_Store` Mac files
- IDE-specific files (`.idea/`, `.vscode/`)
- Build artifacts (`dist/`, `build/`)
- PID files (`.dj_renamer_web.pid`)

**Use `.gitignore`**:
```gitignore
# Python
__pycache__/
*.py[cod]
*.so
.Python
.venv/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Project-specific
.dj_renamer_web.pid
*.log
```

---

## Documentation Standards

### Code Comments

**When to comment**:
- Complex algorithms
- Non-obvious business logic
- Workarounds for bugs
- TODO/FIXME notes

**When NOT to comment**:
- Self-explanatory code
- Obvious operations
- Redundant descriptions

**Examples**:
```python
# ❌ Bad - redundant
# Increment counter by 1
counter += 1

# ✅ Good - explains WHY
# Use counter suffix (1) to avoid filename conflicts
if dst.exists():
    counter = 1
    while (dst.parent / f"{dst.stem}_{counter}{dst.suffix}").exists():
        counter += 1

# ✅ Good - documents workaround
# HACK: librosa sometimes returns BPM as half tempo (e.g., 64 instead of 128)
# Double it if it's suspiciously low
if bpm < 80:
    bpm = bpm * 2
```

### README Files

**Each module should have README.md** explaining:
1. Purpose
2. Usage examples
3. API reference
4. Dependencies
5. Testing instructions

**Example structure**:
```markdown
# Module Name

Brief description.

## Usage

```python
from module import function
result = function(arg)
```

## API Reference

### function(arg: str) -> bool
Description of what it does.

## Testing

```bash
pytest tests/test_module.py
```
```

---

## Performance Guidelines

### Database Queries

**Not applicable** (we don't use database currently)

### File I/O

**Use Path objects**:
```python
from pathlib import Path

# ✅ Good
path = Path("/music/track.mp3")
content = path.read_text()

# ✅ Good - generator for large dirs
for file in path.iterdir():
    if file.is_file():
        process(file)
```

**Avoid repeated disk access**:
```python
# ❌ Bad
if file.exists():
    size = file.stat().st_size
    mtime = file.stat().st_mtime

# ✅ Good
if file.exists():
    stat = file.stat()
    size = stat.st_size
    mtime = stat.st_mtime
```

### API Calls

**Batch requests** when possible:
```python
# ❌ Bad - N API calls
for file in files:
    metadata = api.get_metadata(file)

# ✅ Good - 1 API call
metadata_list = api.get_metadata_batch(files)
```

**Use caching** for repeated data:
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_operation(param):
    # ...
```

---

## Security Guidelines

### Input Validation

**Always validate user input**:
```python
# ✅ Good
from pathlib import Path

def validate_path(path: str) -> Path:
    """Validate and normalize path"""
    p = Path(path).expanduser().resolve()

    # Check it exists
    if not p.exists():
        raise ValueError(f"Path does not exist: {path}")

    # Check it's a directory
    if not p.is_dir():
        raise ValueError(f"Path is not a directory: {path}")

    return p
```

### Path Traversal

**Prevent path traversal attacks**:
```python
# ✅ Good
def is_safe_path(base: Path, target: Path) -> bool:
    """Check if target is within base directory"""
    base = base.resolve()
    target = target.resolve()
    return target.is_relative_to(base)
```

### Sensitive Data

**Never log sensitive data**:
```python
# ❌ Bad
logger.info(f"API key: {api_key}")

# ✅ Good
logger.info(f"API key: {api_key[:4]}...{api_key[-4:]}")

# ✅ Better
logger.info("API key loaded successfully")
```

---

## Deployment Checklist

### Before Production

- [ ] All tests passing
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] CHANGELOG updated
- [ ] Version bumped
- [ ] Dependencies updated
- [ ] Security audit passed
- [ ] Performance tested
- [ ] Error handling verified
- [ ] Logging configured
- [ ] CORS restricted to production domains
- [ ] API rate limiting enabled
- [ ] Backup strategy in place

---

**Last Updated**: 2026-01-29
**Version**: 1.0.0
