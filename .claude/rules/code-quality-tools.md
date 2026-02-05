# Code Quality Tools Reference

Quick reference for common code quality commands.

---

## Python

### Formatting
```bash
# Black (opinionated formatter)
pip install black
black .                          # Format all
black --check .                  # Check only (CI)
black --diff .                   # Show what would change

# Ruff format (faster alternative)
pip install ruff
ruff format .                    # Format all
ruff format --check .            # Check only
```

### Linting
```bash
# Ruff (fast, replaces flake8/isort/pyupgrade)
ruff check .                     # Lint
ruff check . --fix               # Auto-fix
ruff check . --select ALL        # All rules

# Flake8 (traditional)
pip install flake8
flake8 src/ tests/
```

### Type Checking
```bash
# Mypy
pip install mypy
mypy src/                        # Check types
mypy src/ --strict               # Strict mode
mypy src/ --ignore-missing-imports  # Ignore missing stubs
```

### Import Sorting
```bash
# isort
pip install isort
isort .                          # Sort imports
isort . --check                  # Check only
isort . --diff                   # Show diff

# Ruff can also do this
ruff check . --select I --fix
```

### Dead Code
```bash
# Vulture
pip install vulture
vulture src/ --min-confidence 80
vulture src/ tests/ --min-confidence 60  # Include test files
```

### Security
```bash
# Bandit (security linter)
pip install bandit
bandit -r src/                   # Scan for security issues
bandit -r src/ -ll               # Only medium+ severity

# pip-audit (dependency vulnerabilities)
pip install pip-audit
pip-audit

# Safety (alternative)
pip install safety
safety check
```

### All-in-One Commands
```bash
# Full quality check (copy-paste ready)
black . && isort . && ruff check . && mypy src/ && pytest tests/ -v

# CI-friendly (check only, don't modify)
black --check . && isort --check . && ruff check . && mypy src/ && pytest tests/
```

---

## JavaScript / TypeScript

### Formatting
```bash
# Prettier
npm install -D prettier
npx prettier --write .           # Format all
npx prettier --check .           # Check only
```

### Linting
```bash
# ESLint
npm install -D eslint
npx eslint .                     # Lint
npx eslint . --fix               # Auto-fix

# TypeScript-specific
npm install -D @typescript-eslint/parser @typescript-eslint/eslint-plugin
```

### Type Checking
```bash
# TypeScript compiler
npx tsc --noEmit                 # Check types without building
npx tsc                          # Build (also checks types)
```

### Dead Code
```bash
# ts-prune (unused exports)
npx ts-prune

# ESLint rules
npx eslint . --rule 'no-unused-vars: error'
```

### Security
```bash
npm audit                        # Check for vulnerabilities
npm audit fix                    # Auto-fix (careful!)
npm audit --audit-level=high     # Only high+ severity
```

### All-in-One
```bash
# Full quality check
npx prettier --check . && npx eslint . && npx tsc --noEmit && npm test
```

---

## Go

```bash
# Formatting (built-in)
go fmt ./...                     # Format
gofmt -l .                       # List unformatted files

# Linting
golangci-lint run                # Comprehensive linter

# Type checking (built-in with compilation)
go build ./...                   # Build (includes type check)
go vet ./...                     # Additional static analysis

# Security
govulncheck ./...                # Vulnerability check
```

---

## Rust

```bash
# Formatting
cargo fmt                        # Format
cargo fmt -- --check             # Check only

# Linting
cargo clippy                     # Lint
cargo clippy -- -D warnings      # Treat warnings as errors

# Type checking (part of compilation)
cargo check                      # Fast type check without building

# Security
cargo audit                      # Dependency vulnerabilities
```

---

## Pre-commit Hooks

Automate quality checks on every commit:

```bash
pip install pre-commit
```

`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

Install:
```bash
pre-commit install
pre-commit run --all-files  # Test on all files
```

---

## CI/CD Integration

### GitHub Actions (Python)
```yaml
- name: Quality checks
  run: |
    pip install black ruff mypy pytest
    black --check .
    ruff check .
    mypy src/
    pytest tests/ -v
```

### GitHub Actions (Node)
```yaml
- name: Quality checks
  run: |
    npm ci
    npm run lint
    npm run typecheck
    npm test
```

---

## Quick Reference Card

| Task | Python | Node | Go | Rust |
|------|--------|------|-----|------|
| Format | `black .` | `prettier --write .` | `go fmt ./...` | `cargo fmt` |
| Lint | `ruff check .` | `eslint .` | `golangci-lint run` | `cargo clippy` |
| Types | `mypy src/` | `tsc --noEmit` | `go build ./...` | `cargo check` |
| Test | `pytest` | `npm test` | `go test ./...` | `cargo test` |
| Security | `pip-audit` | `npm audit` | `govulncheck ./...` | `cargo audit` |
