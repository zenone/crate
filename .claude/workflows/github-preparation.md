# GitHub Preparation Workflow

**Purpose**: Comprehensive checklist to prepare code for pushing to GitHub, ensuring production-ready, secure, and well-documented repository.

---

## When to Use This Workflow

- Before first push to GitHub (new repository)
- Before major release or version tag
- Before making repository public
- After significant refactoring
- When preparing for team collaboration

---

## Prerequisites

Before starting this workflow:
- [ ] Code is working locally (all features functional)
- [ ] All tests pass
- [ ] No active development in progress (stable state)
- [ ] Backup of current code (just in case)

---

## Phase 1: Code Analysis & Cleanup

### Step 1: Create Code Snapshot (Safety First!)

**Goal**: Save current working version in case cleanup breaks something.

```bash
# Create backup directory
cp -r . ../project-backup-$(date +%Y%m%d-%H%M%S)

# Or create git stash
git add -A
git stash save "Backup before GitHub preparation"

# Or create git branch
git checkout -b pre-github-backup
git add -A
git commit -m "Backup before GitHub preparation"
git checkout main
```

**Verification**:
- [ ] Backup created successfully
- [ ] Can restore if needed

---

### Step 2: Line-by-Line Code Analysis

**Goal**: Identify business logic errors, unused code, and potential issues.

#### Automated Analysis Tools
```bash
# Python
pylint core/ api/ cli/ --reports=y > pylint-report.txt
mypy core/ api/ cli/ --strict
radon cc core/ api/ -s              # Complexity
radon mi core/ api/ -s              # Maintainability
vulture core/ api/ cli/             # Find dead code

# JavaScript/TypeScript
eslint "src/**/*.{js,ts}" --format=stylish
ts-prune                            # Find unused exports

# Generic
sonar-scanner                       # SonarQube analysis
codeclimate analyze                 # Code Climate
```

#### Manual Review Checklist
- [ ] **Business Logic Errors**:
  - Off-by-one errors in loops
  - Incorrect conditional logic
  - Race conditions (async code)
  - Edge case handling (empty inputs, null values)

- [ ] **Error Handling**:
  - Try/except doesn't swallow errors silently
  - Error messages are helpful
  - Proper exception types used
  - Resources cleaned up (files closed, connections closed)

- [ ] **Data Validation**:
  - User input validated before use
  - Type checking on boundaries
  - Range checking for numbers
  - Length limits on strings

- [ ] **Performance Issues**:
  - No N+1 query problems (database)
  - Efficient algorithms (no O(n²) where O(n) possible)
  - No memory leaks
  - No blocking operations on main thread

---

### Step 3: Identify and Remove Unused Code

**Goal**: Clean up dead code without breaking functionality.

#### Find Unused Code
```bash
# Python
vulture core/ api/ cli/ --min-confidence 80

# JavaScript
ts-prune                            # TypeScript unused exports
eslint . --rule 'no-unused-vars: error'

# Go
go-unused ./...

# Manual check
grep -r "def\|class\|function" core/ api/ | cut -d: -f2 | sort | uniq
# Then search each to see if used elsewhere
```

#### Remove Unused Code Safely
**Process**:
1. Identify unused function/class
2. Search entire codebase for usage (be thorough!)
3. If truly unused, comment out (don't delete yet)
4. Run all tests
5. If tests pass, delete commented code
6. Commit: `git commit -m "Remove unused function X"`

**Example**:
```bash
# Find all usages of function
grep -r "old_function_name" . --exclude-dir=.git

# If zero results (except definition), safe to remove
```

**What NOT to Remove**:
- Functions with `@api_endpoint` or similar decorators (may be called by framework)
- CLI commands registered dynamically
- Plugin hooks (even if not used yet)
- Public API functions (breaking change for users)

---

### Step 4: Test Everything After Cleanup

**Goal**: Ensure cleanup didn't break functionality.

```bash
# Run full test suite
pytest tests/ -v --cov=core --cov=api --cov=cli

# Run manually
./cli command1
./cli command2
./cli command3

# Check API endpoints
curl http://localhost:8000/api/endpoint1
curl http://localhost:8000/api/endpoint2
```

**Success Criteria**:
- [ ] All tests pass
- [ ] All features work as before cleanup
- [ ] No new errors or warnings

**If Something Broke**:
1. Restore from backup
2. Identify what was removed that shouldn't have been
3. Restore that code
4. Document in `.claude/knowledge-base/lessons-learned.md`

---

## Phase 2: Security Hardening

### Step 5: Secrets Scanning

**Goal**: Ensure NO secrets in code that will be pushed to GitHub.

#### Automated Scanning
```bash
# Install tools
pip install detect-secrets
brew install gitleaks
brew install truffleHog

# Scan for secrets
gitleaks detect --source . --verbose --report-path gitleaks-report.json
trufflehog filesystem . --json
detect-secrets scan --all-files > .secrets.baseline

# Manual check
grep -r -i "api_key\|secret\|password\|token\|private_key" . \
  --exclude-dir=.git \
  --exclude-dir=.venv \
  --exclude-dir=node_modules \
  --exclude="*.md"
```

#### What to Look For
- [ ] API keys (`OPENAI_API_KEY`, `STRIPE_SECRET_KEY`)
- [ ] Passwords (`password = "admin123"`)
- [ ] Database URLs with credentials (`postgres://user:pass@host/db`)
- [ ] SSH private keys
- [ ] AWS credentials
- [ ] JWT secrets
- [ ] OAuth client secrets

#### Fix Secrets in Code
**Process**:
1. Move secret to environment variable:
   ```python
   # BEFORE (bad)
   API_KEY = "sk-proj-12345678"

   # AFTER (good)
   import os
   API_KEY = os.getenv("OPENAI_API_KEY")
   if not API_KEY:
       raise ValueError("OPENAI_API_KEY environment variable required")
   ```

2. Add to `.env.example` (template without real values):
   ```bash
   # .env.example
   OPENAI_API_KEY=sk-proj-your-key-here
   DATABASE_URL=postgresql://user:pass@localhost/dbname
   JWT_SECRET=your-secret-key-here
   ```

3. Ensure `.env` in `.gitignore`

4. Update documentation with environment variable requirements

---

### Step 6: Remove Secrets from Git History

**If Secrets Already Committed**:

**⚠️ WARNING**: This rewrites git history. Coordinate with team first.

```bash
# Using BFG Repo-Cleaner (recommended)
brew install bfg
bfg --replace-text passwords.txt .git
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Using git-filter-repo
pip install git-filter-repo
git filter-repo --path-glob '**/.env' --invert-paths

# Manual (for specific file)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/secret/file" \
  --prune-empty --tag-name-filter cat -- --all
```

**After Removing**:
1. Rotate all exposed secrets immediately (change API keys, passwords)
2. Force push: `git push origin --force --all`
3. Notify team to re-clone repository

---

### Step 7: Application Security Review

**Goal**: No CRITICAL or HIGH vulnerabilities.

#### Dependency Vulnerabilities
```bash
# Python
pip-audit
safety check
pip list --outdated

# JavaScript/Node
npm audit
npm audit fix  # Auto-fix if possible

# Go
govulncheck ./...

# Rust
cargo audit
```

**Fix Process**:
1. Review each vulnerability
2. Upgrade to patched version: `pip install --upgrade package_name`
3. Test after upgrade (ensure no breaking changes)
4. If no patch available:
   - Check if vulnerability affects your usage
   - Document risk in `README.md` and `.claude/knowledge-base/tech-stack-decisions.md`
   - Plan migration to alternative

**Success Criteria**:
- [ ] No CRITICAL vulnerabilities
- [ ] No HIGH vulnerabilities
- [ ] MEDIUM/LOW documented with mitigation plan

---

#### Static Application Security Testing (SAST)
```bash
# Python
bandit -r core/ api/ cli/ -ll -f json -o bandit-report.json

# JavaScript
npm install -g eslint-plugin-security
eslint . --plugin=security

# Multi-language
semgrep --config auto . --json > semgrep-report.json
```

**Review Findings**:
- [ ] No hardcoded passwords
- [ ] No SQL injection vulnerabilities (use parameterized queries)
- [ ] No command injection (no shell=True with user input)
- [ ] No insecure deserialization (pickle with untrusted input)
- [ ] No weak cryptography (MD5, SHA1 for security)

---

## Phase 3: Repository Cleanup

### Step 8: Unnecessary Files/Directories

**Goal**: Remove development cruft not needed in GitHub repo.

#### What to Remove
**Delete these if present** (after verifying not needed):
```bash
# Build artifacts
rm -rf build/ dist/ *.egg-info/

# Caches
rm -rf __pycache__/ .pytest_cache/ .mypy_cache/ .ruff_cache/
rm -rf node_modules/.cache/

# OS files
find . -name ".DS_Store" -delete
find . -name "Thumbs.db" -delete

# IDE files (if not needed by team)
rm -rf .idea/ .vscode/

# Logs (keep .gitkeep if you want empty logs/ directory)
rm -rf logs/*.log

# Temporary files
rm -rf tmp/ temp/ *.tmp

# Environment files (keep .env.example)
rm .env .env.local .env.*.local
```

#### What to KEEP (Don't Delete!)
- **Working tools**: `.venv/`, `node_modules/`, `vendor/`
- **Configuration**: `.claude/`, `.github/`, `pyproject.toml`, `package.json`
- **Documentation**: `README.md`, `CHANGELOG.md`, `LICENSE`
- **Source code**: `core/`, `api/`, `cli/`, `ui/`, `tests/`

**Remember**: Use `.gitignore` to exclude files from git, don't delete them!

---

### Step 9: Update .gitignore

**Goal**: Comprehensive .gitignore using best practices for your tech stack.

**Process**:
1. Generate base .gitignore:
   ```bash
   # Visit gitignore.io
   curl -L "https://www.toptal.com/developers/gitignore/api/python,node,go,rust,macos,linux,windows,visualstudiocode,jetbrains" > .gitignore
   ```

2. Add project-specific exclusions:
   ```gitignore
   # Environment variables
   .env
   .env.local
   .env.*.local

   # Claude Code local settings
   .claude/settings.local.json
   CLAUDE.local.md

   # Secrets
   secrets/
   *.pem
   *.key
   credentials.json

   # Large files
   *.zip
   *.tar.gz
   data/large_files/

   # Working directories
   .venv/
   venv/
   node_modules/

   # Build artifacts
   dist/
   build/
   *.egg-info/

   # IDE
   .vscode/*
   !.vscode/extensions.json
   !.vscode/settings.json
   .idea/
   *.swp
   *.swo

   # OS
   .DS_Store
   Thumbs.db

   # Logs
   logs/*.log
   *.log

   # Test coverage
   htmlcov/
   .coverage
   coverage.xml

   # Temporary
   tmp/
   temp/
   *.tmp
   ```

3. Test .gitignore:
   ```bash
   # See what would be added
   git add -n .

   # Ensure no .env, secrets, or large files
   git status --ignored
   ```

**Success Criteria**:
- [ ] No secrets will be committed
- [ ] No large binaries will be committed
- [ ] Virtual environments excluded
- [ ] OS-specific files excluded
- [ ] Build artifacts excluded

---

### Step 10: File and Project Naming Review

**Goal**: Ensure optimal naming based on best practices.

#### Research Best Practices
```
Web search:
"[project type] naming conventions 2026"
"best practices for [language] project structure 2026"
```

#### Review Checklist
- [ ] **Project name**: Clear, descriptive, no generic names ("app", "project")
- [ ] **File names**:
  - Consistent case (snake_case for Python, kebab-case for JS)
  - Descriptive (`user_auth.py` not `utils.py`)
  - No abbreviations unless standard (`db` ok, `usr` not ok)

- [ ] **Module names**: Match functionality (`core/auth/` not `core/a/`)
- [ ] **Branding**: Consistent across all files, docs, comments

**If Renaming Needed**:
1. Create rename plan (list all files to rename)
2. Use git mv (preserves history):
   ```bash
   git mv old_name.py new_name.py
   ```
3. Update all imports/references:
   ```bash
   # Find all references
   grep -r "old_name" . --exclude-dir=.git

   # Update each file
   sed -i 's/old_name/new_name/g' file1.py file2.py
   ```
4. Update documentation (README, comments, docstrings)
5. Run all tests
6. Commit: `git commit -m "Rename files for clarity"`

---

## Phase 4: Code Quality & Documentation

### Step 11: Code Comments & Docstrings

**Goal**: Production-ready code comments.

#### Add/Update Docstrings
**Python example**:
```python
def calculate_discount(price: float, discount_percent: float) -> float:
    """Calculate discounted price.

    Args:
        price: Original price in dollars (must be positive)
        discount_percent: Discount as percentage (0-100)

    Returns:
        Final price after discount applied

    Raises:
        ValueError: If price is negative or discount_percent not in range 0-100

    Example:
        >>> calculate_discount(100.0, 20.0)
        80.0
    """
    if price < 0:
        raise ValueError("Price cannot be negative")
    if not 0 <= discount_percent <= 100:
        raise ValueError("Discount must be between 0 and 100")

    return price * (1 - discount_percent / 100)
```

**JavaScript/TypeScript example**:
```typescript
/**
 * Calculate discounted price
 *
 * @param price - Original price in dollars (must be positive)
 * @param discountPercent - Discount as percentage (0-100)
 * @returns Final price after discount applied
 * @throws {Error} If price is negative or discountPercent not in range
 *
 * @example
 * calculateDiscount(100, 20) // returns 80
 */
function calculateDiscount(price: number, discountPercent: number): number {
  if (price < 0) {
    throw new Error("Price cannot be negative");
  }
  if (discountPercent < 0 || discountPercent > 100) {
    throw new Error("Discount must be between 0 and 100");
  }

  return price * (1 - discountPercent / 100);
}
```

#### Remove AI Attribution
```bash
# Find AI attribution comments
grep -r "Generated by Claude\|AI-generated\|Written by AI" . --exclude-dir=.git

# Remove them (manual or automated)
sed -i '/Generated by Claude/d' file.py
```

#### Comment Guidelines
- **DO add comments for**:
  - Complex algorithms (explain approach)
  - Non-obvious business logic (explain why)
  - Workarounds for bugs (explain what and why)
  - Performance-critical sections (explain optimization)

- **DON'T add comments for**:
  - Obvious code (`x = x + 1  # increment x`)
  - What code does (code should be self-documenting)
  - Every single line (noise)

---

### Step 12: Code Style Compliance

**Goal**: Consistent, professional code style.

#### Python: PEP-8
```bash
# Check compliance
flake8 core/ api/ cli/ --max-line-length=100

# Auto-format
black . --line-length=100
isort .  # Sort imports

# Verify
flake8 core/ api/ cli/ --max-line-length=100
```

#### JavaScript/TypeScript: ESLint + Prettier
```bash
# Check
eslint "src/**/*.{js,ts,jsx,tsx}"
prettier --check "src/**/*.{js,ts,jsx,tsx}"

# Auto-format
prettier --write "src/**/*.{js,ts,jsx,tsx}"
eslint "src/**/*.{js,ts,jsx,tsx}" --fix
```

#### Go: gofmt
```bash
gofmt -l .     # Check
gofmt -w .     # Format
```

#### Rust: rustfmt
```bash
cargo fmt -- --check  # Check
cargo fmt             # Format
```

**Success Criteria**:
- [ ] No style violations
- [ ] Consistent indentation (spaces or tabs, not mixed)
- [ ] Imports organized
- [ ] Line length reasonable (< 100-120 chars)

---

### Step 13: Verify API-First Architecture

**Goal**: Confirm all functionality is accessible via API.

#### Checklist
- [ ] **Core Logic** (`core/`):
  - Pure business logic
  - No I/O (no database, no HTTP, no file access)
  - Testable in isolation
  - No framework dependencies

- [ ] **API Layer** (`api/`):
  - Thin wrapper around core logic
  - Input validation
  - Output formatting
  - Error handling and HTTP status codes

- [ ] **CLI/UI Layer** (`cli/`, `ui/`):
  - Calls API (never calls core directly)
  - Presentation logic only
  - User interaction handling

#### Test API-First Structure
```bash
# Can you import and test core without API?
python -c "from core.auth import hash_password; print(hash_password('test'))"
# Should work (no server needed)

# Can you call API programmatically?
curl http://localhost:8000/api/v1/endpoint
# Should work (no CLI needed)

# Can you swap UI?
# Build new UI that calls same API
# Should work without changing core or API
```

**If Not API-First**:
1. Extract business logic from CLI/UI to `core/`
2. Create API endpoints that wrap core logic
3. Refactor CLI/UI to call API
4. See `.claude/workflows/feature-development.md` for detailed steps

---

### Step 14: Verify Test-Driven Development (TDD)

**Goal**: Confirm comprehensive test coverage.

#### Test Coverage
```bash
# Python
pytest tests/ --cov=core --cov=api --cov=cli --cov-report=html
open htmlcov/index.html  # View coverage report

# JavaScript
npm test -- --coverage
open coverage/lcov-report/index.html

# Go
go test ./... -cover -coverprofile=coverage.out
go tool cover -html=coverage.out
```

**Target Coverage**:
- [ ] Core business logic: > 90%
- [ ] API endpoints: > 80%
- [ ] Overall: > 80%

#### Test Quality
- [ ] Tests exist for all features
- [ ] Tests cover happy paths
- [ ] Tests cover error paths
- [ ] Tests cover edge cases
- [ ] Tests are fast (< 5 seconds for unit tests)
- [ ] Tests are independent (can run in any order)
- [ ] No flaky tests (consistently pass/fail)

**If Coverage Low**:
1. Identify untested code
2. Write tests (TDD style: test first)
3. Verify tests fail without code, pass with code
4. Reach target coverage

---

## Phase 5: Documentation & Polish

### Step 15: README.md Excellence

**Goal**: World-class README using 2026 best practices.

#### Research Best Practices
```
Web search:
"best GitHub README 2026"
"README.md template"
"[project type] README examples"
```

#### README Sections (Recommended Structure)
```markdown
# Project Name

Brief description (one sentence)

![Build Status](badge-url) ![Coverage](badge-url) ![License](badge-url)

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Configuration](#configuration)
- [Development](#development)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## Features
- Feature 1: Brief description
- Feature 2: Brief description
- Feature 3: Brief description

## Installation

### Prerequisites
- Python 3.11+ (or other requirements)
- PostgreSQL 14+ (if applicable)

### Install
\`\`\`bash
# Clone repository
git clone https://github.com/username/project.git
cd project

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your settings

# Run migrations (if applicable)
python manage.py migrate

# Start server
python manage.py runserver
\`\`\`

## Quick Start

\`\`\`bash
# Example that works out of the box
./cli hello --name="World"
# Output: Hello, World!
\`\`\`

## Usage

### Basic Usage
\`\`\`python
from project import feature

result = feature.do_something("input")
print(result)  # Output: expected output
\`\`\`

### API Usage
\`\`\`bash
# Example API call
curl -X POST http://localhost:8000/api/v1/endpoint \\
  -H "Content-Type: application/json" \\
  -d '{"key": "value"}'

# Response
{"result": "success"}
\`\`\`

### Advanced Usage
(More complex examples)

## API Documentation

Full API documentation available at: http://localhost:8000/docs

Or see [API.md](docs/API.md) for detailed reference.

## Configuration

### Environment Variables
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | - | Yes |
| `API_KEY` | External API key | - | Yes |
| `DEBUG` | Enable debug mode | `False` | No |

### Configuration File
See `config.example.yml` for configuration options.

## Development

### Project Structure
\`\`\`
project/
├── core/           # Business logic
├── api/            # API endpoints
├── cli/            # CLI interface
├── tests/          # Test suite
└── docs/           # Documentation
\`\`\`

### Development Setup
\`\`\`bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run in development mode
python manage.py runserver --reload
\`\`\`

## Testing

\`\`\`bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=core --cov=api

# Run specific test
pytest tests/test_auth.py::test_login
\`\`\`

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License. See [LICENSE](LICENSE) file for details.

## Credits

Built with ❤️ using [technologies]

## Support

- Documentation: https://docs.example.com
- Issues: https://github.com/username/project/issues
- Email: support@example.com
\`\`\`

#### Make README Entertaining & Accessible
**Tips**:
- Use analogies for complex concepts
- Add emojis sparingly (visual interest)
- Use simple language (avoid jargon)
- Include diagrams or architecture images
- Add "Why This Project?" section (motivation)
- Include success stories or testimonials

**Bad Example** (too technical):
> "This application implements a RESTful API using a layered architecture with dependency injection for service orchestration."

**Good Example** (accessible):
> "Think of this app as a Swiss Army knife for managing your data. It's like having a personal assistant that automatically organizes, processes, and secures your information—all through simple commands or clicks."

#### Test README Examples
**CRITICAL**: Copy-paste every code example and verify it works!

```bash
# Test each command
cat README.md | grep '```bash' -A 10 | grep -v '```' > test-commands.sh
bash test-commands.sh  # Ensure all commands work
```

**Success Criteria**:
- [ ] All examples tested and working
- [ ] Installation instructions complete and accurate
- [ ] Quick Start section takes < 5 minutes
- [ ] Uses simple, accessible language
- [ ] Includes table of contents for navigation
- [ ] Has visual interest (badges, diagrams, code blocks)

---

### Step 16: Additional Documentation

#### CHANGELOG.md
```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Feature X for improved performance
- New API endpoint `/api/v2/feature`

### Changed
- Updated authentication to use JWT

### Deprecated
- Old API endpoint `/api/v1/old` (use `/api/v2/new` instead)

### Removed
- Support for Python 3.8 (now requires 3.9+)

### Fixed
- Bug where feature Y crashed on edge case

### Security
- Fixed XSS vulnerability in input validation

## [1.0.0] - 2026-02-01

### Added
- Initial release
- User authentication
- API endpoints
- CLI interface
```

#### LICENSE
Choose appropriate license:
- MIT: Permissive, allows commercial use
- Apache 2.0: Permissive, includes patent grant
- GPL v3: Copyleft, derivatives must be open source
- Proprietary: Custom license for closed-source

Generate at: https://choosealicense.com/

#### CONTRIBUTING.md
```markdown
# Contributing to [Project Name]

Thank you for considering contributing!

## Code of Conduct
Be respectful, inclusive, and constructive.

## How to Contribute
1. Fork the repository
2. Create a branch (`git checkout -b feature/amazing-feature`)
3. Make changes
4. Write tests
5. Ensure all tests pass (`pytest tests/`)
6. Update documentation
7. Commit (`git commit -m 'Add amazing feature'`)
8. Push (`git push origin feature/amazing-feature`)
9. Open Pull Request

## Development Guidelines
- Follow TDD (test-driven development)
- Maintain API-first architecture
- Write clear commit messages
- Update documentation with code changes
- Ensure all tests pass before submitting PR

## Questions?
Open an issue or email maintainer@example.com
```

---

## Phase 6: Final Review & Push

### Step 17: Manual Testing Checkpoint

**Goal**: Final verification before pushing to GitHub.

#### Test All Features
- [ ] Run application locally
- [ ] Test each major feature manually
- [ ] Test error cases
- [ ] Verify API endpoints
- [ ] Test CLI commands
- [ ] Check UI (if applicable)

#### Test Installation (Fresh Environment)
```bash
# Create fresh environment
python -m venv test-env
source test-env/bin/activate

# Follow README installation instructions exactly
# (This tests if your README is accurate)

# Deactivate when done
deactivate
rm -rf test-env
```

**If Installation Fails**:
1. Fix issue
2. Update README
3. Test again

---

### Step 18: Update .claude/ Documentation

**Goal**: Perfect memory for future Claude sessions.

#### Update Files
- [ ] `.claude/state/current-state.md`:
  ```markdown
  **Phase**: Ready for GitHub push
  **Last Action**: Completed GitHub preparation workflow
  **Next Steps**: Push to GitHub, set up CI/CD
  ```

- [ ] `.claude/knowledge-base/lessons-learned.md`:
  - Add any issues found during cleanup
  - Document what worked well in preparation process

- [ ] `.claude/knowledge-base/tech-stack-decisions.md`:
  - Document any library upgrades or changes

---

### Step 19: Git Repository Preparation

#### Initialize Git (if not already)
```bash
# Check if git initialized
git status

# If not, initialize
git init
git branch -M main
```

#### Review Git Status
```bash
git status
git status --ignored  # Verify .gitignore working
```

**Checklist**:
- [ ] Only intended files will be committed
- [ ] .env and secrets excluded
- [ ] .venv or node_modules excluded
- [ ] Build artifacts excluded

#### Stage and Commit
```bash
# Stage all files
git add .

# Review what will be committed
git diff --staged --stat

# Commit
git commit -m "$(cat <<'EOF'
Initial commit: Production-ready codebase

- Implemented core features with TDD
- API-first architecture
- Comprehensive test suite (>80% coverage)
- Security hardened (no secrets, dependencies scanned)
- Complete documentation (README, API docs, inline comments)
- Automated quality checks (pre-commit hooks)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Step 20: GitHub Repository Setup

#### If Existing GitHub Repo (Delete and Start Fresh)
```bash
# Backup existing repo (if needed)
# Then delete on GitHub web interface

# Remove old remote
git remote remove origin
```

#### Create New GitHub Repository
1. Go to https://github.com/new
2. Repository name: `[your-project-name]`
3. Description: Brief description
4. Visibility: Public or Private
5. Do NOT initialize with README (we have one)
6. Click "Create repository"

#### Add Remote and Push
```bash
# Add remote
git remote add origin git@github.com:username/project-name.git

# Or with HTTPS
git remote add origin https://github.com/username/project-name.git

# Verify remote
git remote -v

# Push
git push -u origin main
```

**If SSH Key Issues** (see Step 21)

---

### Step 21: SSH Key Setup (If Needed)

**If you get "Permission denied (publickey)" error**:

#### Check Existing SSH Keys
```bash
ls -la ~/.ssh/
# Look for: id_rsa.pub, id_ed25519.pub, id_ecdsa.pub
```

#### Generate New SSH Key (if needed)
```bash
# Generate key
ssh-keygen -t ed25519 -C "your_email@example.com"

# When prompted:
# - File location: Press Enter (default)
# - Passphrase: Optional (recommended for security)

# Start ssh-agent
eval "$(ssh-agent -s)"

# Add key to ssh-agent
ssh-add ~/.ssh/id_ed25519

# Copy public key
cat ~/.ssh/id_ed25519.pub | pbcopy  # macOS
# Or manually copy output of: cat ~/.ssh/id_ed25519.pub
```

#### Add SSH Key to GitHub
1. Go to https://github.com/settings/keys
2. Click "New SSH key"
3. Title: "MacBook Pro" (or your computer name)
4. Key type: Authentication Key
5. Key: Paste copied public key
6. Click "Add SSH key"

#### Test SSH Connection
```bash
ssh -T git@github.com
# Should see: "Hi username! You've successfully authenticated..."
```

#### Try Push Again
```bash
git push -u origin main
```

---

### Step 22: GitHub Repository Configuration

#### Add Repository Description
1. Go to repository page
2. Click "⚙️" (settings) → About
3. Add description
4. Add topics/tags
5. Add website (if applicable)

#### Enable Features
- [ ] Issues (for bug tracking)
- [ ] Projects (for project management)
- [ ] Wiki (for documentation)
- [ ] Discussions (for community)

#### Set Branch Protection (Recommended)
1. Settings → Branches → Add rule
2. Branch name pattern: `main`
3. Enable:
   - [ ] Require a pull request before merging
   - [ ] Require status checks to pass before merging
   - [ ] Require conversation resolution before merging

#### Add Topics
Click "⚙️" → Topics:
- Add relevant tags: `python`, `api`, `cli`, `automation`, etc.

---

## Phase 7: CI/CD Setup (Optional but Recommended)

### Step 23: GitHub Actions Workflow

Create `.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Lint
      run: |
        flake8 core/ api/ cli/ --max-line-length=100

    - name: Type check
      run: |
        mypy core/ api/ cli/ --ignore-missing-imports

    - name: Test
      run: |
        pytest tests/ -v --cov=core --cov=api --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

    - name: Security scan
      run: |
        pip install bandit safety
        bandit -r core/ api/ cli/ -ll
        safety check
```

**Push workflow**:
```bash
git add .github/workflows/ci.yml
git commit -m "Add CI/CD workflow"
git push
```

**Verify**:
- Go to repository → Actions tab
- Workflow should run automatically

---

## Success Criteria

GitHub preparation is **COMPLETE** when:
- ✅ All code reviewed and tested
- ✅ No secrets in code or git history
- ✅ No CRITICAL/HIGH security vulnerabilities
- ✅ .gitignore properly configured
- ✅ Code style consistent (formatted and linted)
- ✅ All files properly named
- ✅ API-first architecture verified
- ✅ TDD verified (>80% test coverage)
- ✅ README.md complete and tested
- ✅ Documentation comprehensive
- ✅ .claude/ knowledge base updated
- ✅ Git repository clean and committed
- ✅ Pushed to GitHub successfully
- ✅ CI/CD configured (optional)

---

## Post-Push Checklist

After successful push:
- [ ] Verify repository looks good on GitHub
- [ ] Check CI/CD runs and passes
- [ ] Add repository URL to `.claude/state/current-state.md`
- [ ] Share with team (if applicable)
- [ ] Create first release/tag (if ready):
  ```bash
  git tag -a v1.0.0 -m "Initial release"
  git push origin v1.0.0
  ```

---

## Troubleshooting

### Common Issues

#### "Too many files to push"
**Solution**: Check .gitignore and remove node_modules/, .venv/, etc.

#### "SSH Key Permission Denied"
**Solution**: See Step 21 for SSH setup

#### "Secrets detected in code"
**Solution**: See Step 5-6 for secret removal

#### "Tests fail in CI but pass locally"
**Solution**: Environment differences. Check Python version, dependencies, environment variables.

#### "Cannot push to main (protected branch)"
**Solution**: Create feature branch, push that, create pull request.

---

*This workflow ensures your code is production-ready, secure, and professional before publishing to GitHub. Never skip the security steps!*
