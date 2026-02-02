# Contributing to Crate

First off, thank you for considering contributing to Crate! 🎵

DJs helping DJs make this tool better. Whether you're fixing a bug, adding a feature, or improving documentation, your contributions are welcome.

## Ways to Contribute

### 1. Report Bugs
Found a bug? Help us fix it!

**Before submitting**:
- Check if the bug is already reported in [Issues](https://github.com/yourusername/crate/issues)
- Try the latest version (`git pull` and restart)

**When reporting**:
- Use a clear, descriptive title
- Describe the expected vs actual behavior
- Include steps to reproduce
- Add screenshots/logs if helpful
- Mention your OS and browser

**Template**:
```
**Bug**: Files not renaming when using {track} variable

**Expected**: Files should be renamed with track numbers
**Actual**: Files are skipped

**Steps to Reproduce**:
1. Load directory with album
2. Use template: `{track}. {artist} - {title}`
3. Click Rename Selected
4. All files skipped

**Environment**:
- OS: macOS 14.2
- Browser: Chrome 120
- Crate version: v1.0.0

**Logs**:
(paste console errors here)
```

### 2. Suggest Features
Have an idea? We'd love to hear it!

**Good feature requests**:
- Explain the problem you're trying to solve
- Describe your proposed solution
- Mention if you'd like to implement it yourself

**Example**:
```
**Feature**: FLAC file support

**Problem**: Many DJs use FLAC for archival quality

**Proposal**: Extend metadata parsing to handle FLAC tags

**I can help**: Yes, I've worked with mutagen before
```

### 3. Improve Documentation
- Fix typos or unclear explanations
- Add missing information
- Create tutorials or guides
- Improve code comments

### 4. Write Code
Ready to code? Awesome!

## Development Setup

### Prerequisites
- Python 3.8+ (3.14 recommended)
- Git
- Virtual environment tool

### Quick Start
```bash
# Clone the repo
git clone https://github.com/yourusername/crate.git
cd crate

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies (including dev tools)
pip install -e ".[dev]"

# Start the web UI
./start_crate_web.sh

# Or start manually
uvicorn web.main:app --reload
```

### Running Tests
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_api.py -v

# Run with coverage
pytest tests/ --cov=crate --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Code Style
We use:
- **Black** for Python formatting
- **Ruff** for Python linting
- **Prettier** for JavaScript formatting (optional)

```bash
# Format Python code
black crate/ tests/

# Check linting
ruff check crate/

# Fix auto-fixable issues
ruff check --fix crate/
```

## Pull Request Process

### 1. Fork & Branch
```bash
# Fork the repo on GitHub, then:
git clone https://github.com/YOUR_USERNAME/crate.git
cd crate

# Create a feature branch
git checkout -b feature/amazing-feature

# Or for bug fixes:
git checkout -b fix/bug-description
```

### 2. Make Your Changes
- Write clear, focused commits
- Follow existing code style
- Add tests for new features
- Update documentation if needed

**Commit Messages**:
```bash
# Good commits:
git commit -m "feat: Add FLAC file support"
git commit -m "fix: Resolve collision detection bug"
git commit -m "docs: Update template variable examples"

# Format: <type>: <description>
# Types: feat, fix, docs, style, refactor, test, chore
```

### 3. Test Your Changes
```bash
# Run the full test suite
pytest tests/ -v

# Test manually in the web UI
./start_crate_web.sh

# Test edge cases:
# - Empty directories
# - Files with no metadata
# - Unicode characters in filenames
# - Large libraries (1000+ files)
```

### 4. Update Documentation
- Add docstrings to new functions
- Update README.md if user-facing
- Add entry to CHANGELOG.md (Unreleased section)

### 5. Submit Pull Request
```bash
# Push your branch
git push origin feature/amazing-feature

# Create PR on GitHub with:
# - Clear title describing the change
# - Description of what and why
# - Link to related issue (if any)
# - Screenshots/GIFs for UI changes
```

**PR Template**:
```
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement

## Testing
- [ ] All tests passing
- [ ] Added new tests for this change
- [ ] Manually tested in web UI

## Screenshots (if applicable)
(add screenshots here)

## Checklist
- [ ] Code follows project style
- [ ] Self-reviewed the code
- [ ] Commented complex logic
- [ ] Updated documentation
- [ ] No breaking changes (or documented)
```

## Project Structure

```
crate/
├── crate/              # Core business logic
│   ├── core/          # Pure functions (no I/O)
│   │   ├── metadata.py       # Metadata extraction
│   │   ├── template.py       # Template expansion
│   │   ├── key_conversion.py # Camelot wheel
│   │   └── sanitization.py   # Filename safety
│   ├── api/           # API layer
│   │   └── renamer.py        # RenamerAPI class
│   └── cli/           # Command-line interface
├── web/               # Web UI
│   ├── main.py        # FastAPI backend
│   ├── streaming.py   # SSE progress
│   └── static/        # Frontend assets
│       ├── index.html
│       ├── js/app.js
│       └── css/styles.css
├── tests/             # Test suite
└── docs/              # Documentation
```

## Architecture Principles

### 1. API-First Design
All functionality is accessible through the API before building UI.

**Why**: Easier testing, future flexibility (swap UI frameworks, add mobile, etc.)

### 2. Pure Core Functions
The `core/` module contains pure functions with no I/O side effects.

**Benefits**: Easy to test, easy to reason about, reusable

### 3. Separation of Concerns
- **Core**: Business logic (metadata, templates, audio)
- **API**: Wraps core, handles I/O
- **Web/CLI**: Thin clients that call API

## Coding Guidelines

### Python
- Use type hints for function parameters and returns
- Write docstrings for public functions
- Keep functions focused and small
- Avoid global state
- Use pathlib.Path for file paths

```python
def extract_metadata(file_path: Path) -> Dict[str, str]:
    """
    Extract ID3 metadata from an MP3 file.

    Args:
        file_path: Path to the MP3 file

    Returns:
        Dictionary of metadata fields (artist, title, etc.)

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is not valid MP3
    """
    # Implementation here
```

### JavaScript
- Use modern ES6+ features
- Avoid jQuery or frameworks (vanilla JS)
- Clear variable names
- Add comments for complex logic
- Handle errors gracefully

```javascript
async loadDirectory(path) {
    try {
        const result = await this.api.listDirectory(path);
        this.displayFiles(result.files);
    } catch (error) {
        this.ui.error(`Failed to load directory: ${error.message}`);
    }
}
```

### CSS
- Use CSS variables for theming
- Mobile-first responsive design
- Clear class names (BEM-style preferred)
- Avoid !important

## Testing Guidelines

### Write Tests For
- New features (100% coverage goal)
- Bug fixes (add regression test)
- Edge cases (empty input, Unicode, large data)
- Error handling

### Test Structure
```python
class TestFeatureName:
    def test_basic_functionality(self):
        """Test the happy path"""
        # Arrange
        input_data = create_test_data()

        # Act
        result = function_under_test(input_data)

        # Assert
        assert result.status == "success"
        assert result.renamed_count == 5

    def test_error_handling(self):
        """Test error conditions"""
        with pytest.raises(ValueError):
            function_under_test(invalid_input)
```

## Common Tasks

### Adding a New Template Variable
1. Update `crate/core/metadata.py` to extract the field
2. Add to `crate/core/template.py` template expansion
3. Update documentation in README.md
4. Add tests in `tests/test_template.py`
5. Update UI variable buttons in `index.html`

### Adding a New Feature Flag
1. Add to `DEFAULT_CONFIG` in `crate/core/config.py`
2. Add UI control in `web/static/index.html`
3. Read flag in `web/static/js/app.js`
4. Respect flag in business logic
5. Document in README.md settings section

### Fixing a Bug
1. Create a failing test that reproduces the bug
2. Fix the bug
3. Verify test passes
4. Add entry to CHANGELOG.md

## Need Help?

- **Questions**: Open a [Discussion](https://github.com/yourusername/crate/discussions)
- **Bugs**: Open an [Issue](https://github.com/yourusername/crate/issues)
- **Chat**: Join our Discord (link in README)
- **Email**: your.email@example.com

## Code of Conduct

Be respectful, inclusive, and professional. We're all here to make DJ life easier.

- Be welcoming to newcomers
- Respect differing viewpoints
- Accept constructive criticism gracefully
- Focus on what's best for the community

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to Crate! 🎧**

Your efforts help DJs worldwide spend less time renaming files and more time making music.
