# Quality Assurance Workflow

**Purpose**: Comprehensive checklist to ensure code quality before committing or deploying.

---

## When to Use This Workflow

- Before every git commit
- Before creating pull requests
- Before deploying to staging/production
- After fixing bugs (ensure no regressions)
- During code reviews

---

## Quick Checklist (TL;DR)

For impatient developers (but please read full workflow at least once):

```markdown
- [ ] All tests pass (unit + integration)
- [ ] No regressions
- [ ] Code formatted and linted
- [ ] Security review passed
- [ ] Documentation updated
- [ ] No secrets in code
- [ ] Knowledge base updated
```

---

## Full QA Workflow

### 1. Automated Testing

#### Unit Tests
**Goal**: Verify individual functions work in isolation

**Commands** (language-specific examples):
```bash
# Python
pytest tests/unit/ -v --cov=core

# JavaScript/Node
npm test -- --coverage

# Go
go test ./... -cover

# Rust
cargo test
```

**Success Criteria**:
- [ ] All unit tests pass
- [ ] Code coverage > 80% (for new code)
- [ ] No skipped tests without documented reason
- [ ] Tests run in < 30 seconds (fast feedback)

---

#### Integration Tests
**Goal**: Verify components work together

**Commands**:
```bash
# Python
pytest tests/integration/ -v

# JavaScript/Node
npm run test:integration

# Docker-based integration
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

**Success Criteria**:
- [ ] All integration tests pass
- [ ] Database migrations tested (if applicable)
- [ ] External API mocks work correctly
- [ ] Error handling tested (not just happy paths)

---

#### End-to-End Tests
**Goal**: Verify system works from user's perspective

**Commands**:
```bash
# Web: Playwright/Cypress
npm run test:e2e

# CLI: Test actual command execution
./tests/e2e/run-all.sh

# API: Test via HTTP client
newman run api-tests.postman_collection.json
```

**Success Criteria**:
- [ ] Critical user flows work
- [ ] UI renders correctly (if applicable)
- [ ] APIs return correct responses
- [ ] Error messages are user-friendly

---

#### Regression Tests
**Goal**: Ensure new changes didn't break existing features

**Process**:
1. Run ENTIRE test suite (not just new tests)
2. Test previously buggy areas (check issues history)
3. Test features that interact with changed code
4. Check for performance degradation

**Success Criteria**:
- [ ] All existing tests still pass
- [ ] No new warnings or errors in logs
- [ ] Response times haven't increased significantly
- [ ] Memory usage hasn't increased significantly

---

### 2. Code Quality Checks

#### Code Formatting
**Goal**: Consistent code style across project

**Tools**:
```bash
# Python
black . --check                    # Check formatting
black .                            # Apply formatting

# JavaScript
prettier --check "src/**/*.{js,ts,jsx,tsx}"
prettier --write "src/**/*.{js,ts,jsx,tsx}"

# Go
gofmt -l .                         # Check
gofmt -w .                         # Format

# Rust
cargo fmt -- --check               # Check
cargo fmt                          # Format
```

**Success Criteria**:
- [ ] No formatting changes needed (or applied)
- [ ] Consistent indentation (spaces or tabs, not mixed)
- [ ] Line length < 100-120 characters

---

#### Linting
**Goal**: Catch common errors and enforce best practices

**Tools**:
```bash
# Python
flake8 core/ api/ cli/             # Style guide enforcement
pylint core/ api/ cli/             # Deeper analysis
ruff check .                       # Fast modern linter

# JavaScript/TypeScript
eslint "src/**/*.{js,ts,jsx,tsx}"

# Go
golangci-lint run

# Rust
cargo clippy -- -D warnings
```

**Success Criteria**:
- [ ] No errors (E)
- [ ] No warnings (W) unless documented exception
- [ ] No code complexity warnings (C)
- [ ] No style violations (R)

**Common Issues to Fix**:
- Unused imports/variables
- Undefined names
- Incorrect types
- Code too complex (refactor)
- Missing docstrings

---

#### Type Checking
**Goal**: Verify type safety (if applicable)

**Tools**:
```bash
# Python
mypy core/ api/ cli/ --strict

# TypeScript
tsc --noEmit

# Go
go vet ./...
```

**Success Criteria**:
- [ ] No type errors
- [ ] All public functions have type annotations
- [ ] No `any` types in TypeScript (or minimal with justification)
- [ ] No `# type: ignore` without comment explaining why

---

#### Code Complexity
**Goal**: Keep code maintainable

**Tools**:
```bash
# Python
radon cc core/ api/ -a           # Cyclomatic complexity
radon mi core/ api/ -s           # Maintainability index
xenon --max-absolute B --max-modules B --max-average A .

# JavaScript
npx eslint . --ext .js,.ts --rule 'complexity: ["error", 10]'

# Generic
sonar-scanner                     # SonarQube
```

**Success Criteria**:
- [ ] Cyclomatic complexity < 10 per function
- [ ] Maintainability index > 65 (A or B rating)
- [ ] No functions > 50 lines (extract helpers)
- [ ] No files > 500 lines (split into modules)

---

### 3. Security Review

#### Secrets Scanning
**Goal**: Ensure no credentials committed

**Tools**:
```bash
# git-secrets
git secrets --scan

# truffleHog
trufflehog filesystem . --json

# gitleaks
gitleaks detect --source . --verbose

# Manual check
grep -r "API_KEY\|SECRET\|PASSWORD\|TOKEN" . --exclude-dir=.git
```

**Success Criteria**:
- [ ] No API keys, tokens, passwords in code
- [ ] No `.env` files committed (should be in .gitignore)
- [ ] No hardcoded URLs with credentials
- [ ] Secrets stored in environment variables or secret manager

**What to Look For**:
- `API_KEY = "sk-..."`
- `password = "admin123"`
- `mysql://user:pass@host/db`
- `AWS_SECRET_ACCESS_KEY = "..."`

---

#### Dependency Vulnerabilities
**Goal**: No known CVEs in dependencies

**Tools**:
```bash
# Python
pip-audit                         # Check pip packages
safety check                      # Check against safety DB
pipenv check                      # If using pipenv

# JavaScript/Node
npm audit                         # Built-in
yarn audit                        # If using yarn
snyk test                         # Advanced scanning

# Go
govulncheck ./...

# Rust
cargo audit

# Generic (works for all)
trivy fs .                        # Trivy scanner
```

**Success Criteria**:
- [ ] No CRITICAL vulnerabilities
- [ ] No HIGH vulnerabilities
- [ ] MEDIUM/LOW documented with mitigation plan (if can't upgrade)

**If Vulnerabilities Found**:
1. Upgrade to patched version
2. If no patch available:
   - Check if vulnerability affects your usage
   - Document risk in `.claude/knowledge-base/tech-stack-decisions.md`
   - Plan migration to alternative library

---

#### OWASP Top 10 Check
**Goal**: Prevent common web vulnerabilities

**Manual Checklist**:
- [ ] **A01: Broken Access Control**
  - Authorization checked on every protected endpoint?
  - Users can't access other users' data?

- [ ] **A02: Cryptographic Failures**
  - Passwords hashed (not encrypted or plaintext)?
  - Sensitive data encrypted at rest and in transit (HTTPS)?

- [ ] **A03: Injection**
  - SQL queries use parameterized statements?
  - User input sanitized before use in commands?
  - No `eval()` or `exec()` with user input?

- [ ] **A04: Insecure Design**
  - Rate limiting on authentication endpoints?
  - No security-critical logic in client-side code?

- [ ] **A05: Security Misconfiguration**
  - Debug mode disabled in production?
  - Default credentials changed?
  - Unnecessary features disabled?

- [ ] **A06: Vulnerable and Outdated Components**
  - Dependencies up to date? (see Dependency Vulnerabilities above)

- [ ] **A07: Identification and Authentication Failures**
  - Strong password requirements enforced?
  - Multi-factor authentication available (for sensitive apps)?
  - Session tokens secure (httpOnly, secure, sameSite)?

- [ ] **A08: Software and Data Integrity Failures**
  - Dependencies from trusted sources?
  - CI/CD pipeline secure?

- [ ] **A09: Security Logging and Monitoring Failures**
  - Failed login attempts logged?
  - Suspicious activity alerting configured?

- [ ] **A10: Server-Side Request Forgery (SSRF)**
  - User-provided URLs validated against allowlist?
  - No arbitrary URL fetching?

**Tools**:
```bash
# Python
bandit -r core/ api/              # Security linter

# JavaScript
npm audit                         # Includes security checks

# Static Application Security Testing (SAST)
semgrep --config auto .           # Open-source SAST

# Dynamic Application Security Testing (DAST)
zap-cli quick-scan http://localhost:8000  # OWASP ZAP
```

---

### 4. Performance Testing (Optional but Recommended)

#### Load Testing
**Goal**: Ensure system handles expected load

**Tools**:
```bash
# HTTP load testing
ab -n 1000 -c 10 http://localhost:8000/api/endpoint     # Apache Bench
wrk -t4 -c100 -d30s http://localhost:8000/              # wrk
k6 run load-test.js                                     # k6

# CLI load testing
for i in {1..1000}; do ./cli command & done; wait
```

**Success Criteria**:
- [ ] Response time < 200ms (p95) for API endpoints
- [ ] No errors under normal load
- [ ] Memory usage stable (no leaks)
- [ ] CPU usage reasonable (< 80% under load)

---

#### Profiling
**Goal**: Identify performance bottlenecks

**Tools**:
```bash
# Python
python -m cProfile script.py              # CPU profiling
memray run script.py                      # Memory profiling

# JavaScript
node --prof script.js                     # CPU profiling

# Go
go test -cpuprofile=cpu.prof
go test -memprofile=mem.prof

# Rust
cargo flamegraph
```

**When to Profile**:
- New feature is slow (> 1 second for simple operations)
- Memory usage unexpectedly high
- Before optimizing (measure first!)

---

### 5. Documentation Quality

#### Code Documentation
**Checklist**:
- [ ] All public functions have docstrings
  ```python
  def calculate_tax(amount: float, rate: float) -> float:
      """Calculate tax on given amount.

      Args:
          amount: Pre-tax amount in dollars
          rate: Tax rate as decimal (0.08 for 8%)

      Returns:
          Tax amount in dollars

      Raises:
          ValueError: If amount or rate is negative
      """
  ```

- [ ] Complex logic has comments explaining WHY (not WHAT)
  ```python
  # Use exponential backoff to avoid overwhelming API during outages
  for attempt in range(max_retries):
      try:
          response = api.call()
          break
      except APIError:
          sleep(2 ** attempt)
  ```

- [ ] No AI attribution comments (remove "Generated by Claude")
- [ ] No TODO/FIXME comments (fix or create task)
- [ ] No commented-out code (delete it, git remembers)

---

#### External Documentation
**Checklist**:
- [ ] README.md updated with new features
- [ ] README.md examples work (copy-paste tested)
- [ ] API documentation regenerated (if using OpenAPI/Swagger)
- [ ] Changelog updated (CHANGELOG.md)
- [ ] Migration guide (if breaking changes)

**Example README Section**:
```markdown
## Features

### User Authentication
Secure JWT-based authentication with bcrypt password hashing.

**Usage**:
\`\`\`bash
# Login
curl -X POST http://localhost:8000/api/v1/login \\
  -H "Content-Type: application/json" \\
  -d '{"username": "user", "password": "pass"}'

# Response
{"token": "eyJhbGciOiJIUzI1NiIs..."}
\`\`\`

**Configuration**:
- `JWT_SECRET`: Secret key for signing tokens (required)
- `JWT_EXPIRATION`: Token lifetime in seconds (default: 86400)
```

---

### 6. Manual Testing

#### Functional Testing
**Process**:
1. Test happy path (everything works)
2. Test error paths (invalid input, missing data)
3. Test edge cases (empty strings, very large numbers, unicode)
4. Test as different user roles (admin, user, guest)

**Example Test Cases** (for login feature):
```markdown
Happy Path:
- [ ] Can login with correct credentials → Returns token

Error Paths:
- [ ] Login with wrong password → Returns 401
- [ ] Login with non-existent user → Returns 401
- [ ] Login with missing password → Returns 400
- [ ] Login with empty string password → Returns 400

Edge Cases:
- [ ] Login with username containing spaces
- [ ] Login with username containing unicode (测试)
- [ ] Login with very long password (>1000 chars)
- [ ] Login 10 times rapidly (rate limiting works?)

Security:
- [ ] Login with SQL injection attempt (admin' OR '1'='1)
- [ ] Login with XSS attempt (<script>alert(1)</script>)
```

---

#### UI/UX Testing (if applicable)
**Checklist**:
- [ ] UI renders correctly (no layout issues)
- [ ] Buttons clickable and responsive
- [ ] Forms validate input
- [ ] Error messages clear and actionable
- [ ] Loading states shown (spinners, skeletons)
- [ ] Mobile responsive (if web app)
- [ ] Keyboard navigation works (accessibility)
- [ ] Screen reader compatible (test with VoiceOver/NVDA)
- [ ] Dark mode works (if supported)

**Test Browsers** (if web app):
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (if on Mac)

---

### 7. Pre-Commit Final Checks

#### Git Status Clean
```bash
git status
```

**Checklist**:
- [ ] Only intended files staged
- [ ] No `.env` or secret files staged
- [ ] No large binary files accidentally added
- [ ] .gitignore correctly configured

---

#### Build Success
```bash
# Python
python -m build

# JavaScript/Node
npm run build

# Go
go build ./...

# Rust
cargo build --release
```

**Success Criteria**:
- [ ] Build completes without errors
- [ ] No warnings (or documented exceptions)

---

#### Final Review
**Checklist**:
- [ ] Read your own diff (`git diff --staged`)
- [ ] Check for:
  - Debug print statements
  - Hardcoded values that should be configurable
  - Typos in comments or strings
  - Overly long functions (should be refactored)
  - Magic numbers (should be named constants)

---

### 8. Knowledge Base Updates

**Files to Update**:
- [ ] `.claude/state/current-state.md`:
  - Move task to "Completed"
  - Add to "Recent Changes"
  - Update "Next Steps"

- [ ] `.claude/knowledge-base/lessons-learned.md`:
  - Add any bugs fixed
  - Document gotchas discovered
  - Note what worked well

**Example Update**:
```markdown
## [2026-02-01] Login Rate Limiting

**Problem**: Forgot to test rate limiting under load

**Solution**: Added load test with 100 rapid requests

**Prevention**: Add load testing to QA checklist for auth features

**Tags**: #testing #security #authentication
```

---

## QA Automation

### Pre-Commit Hook (Recommended)
**Setup**:
```bash
# .git/hooks/pre-commit
#!/bin/bash
set -e

echo "Running pre-commit checks..."

# Format check
black --check . || (echo "❌ Code not formatted. Run: black ." && exit 1)

# Lint
flake8 core/ api/ cli/ || (echo "❌ Linting failed" && exit 1)

# Type check
mypy core/ api/ cli/ || (echo "❌ Type check failed" && exit 1)

# Tests
pytest tests/ -v || (echo "❌ Tests failed" && exit 1)

# Security
bandit -r core/ api/ -ll || (echo "❌ Security issues found" && exit 1)

echo "✅ All checks passed!"
```

**Make it executable**:
```bash
chmod +x .git/hooks/pre-commit
```

---

### CI/CD Pipeline
**Example GitHub Actions** (`.github/workflows/ci.yml`):
```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements-dev.txt
      - name: Format check
        run: black --check .
      - name: Lint
        run: flake8 core/ api/ cli/
      - name: Type check
        run: mypy core/ api/ cli/
      - name: Test
        run: pytest tests/ -v --cov=core --cov=api
      - name: Security scan
        run: bandit -r core/ api/ -ll
```

---

## Quality Metrics Dashboard

Track these over time:
- Test coverage %
- Number of tests
- Build time
- Lines of code
- Code complexity
- Security vulnerabilities
- Performance (response time)

**Tools**: SonarQube, Code Climate, Codecov

---

## When to Skip Parts of This Workflow

### You Can Skip If...
- **Load testing**: For internal tools with < 10 users
- **E2E tests**: For libraries (no UI)
- **Performance profiling**: If not a performance-critical feature
- **Manual UI testing**: For CLI-only apps

### You Cannot Skip
- Unit tests (always required)
- Security review (always required)
- Code formatting/linting (always required)
- Documentation updates (always required)
- Knowledge base updates (always required)

---

## Red Flag Checklist

**STOP and fix immediately if you see**:
- ❌ Tests disabled or commented out
- ❌ Secrets in code (even in comments)
- ❌ SQL queries with string concatenation
- ❌ `eval()` or `exec()` with user input
- ❌ `try/except pass` (silent error swallowing)
- ❌ Passwords in plaintext or encrypted (must be hashed)
- ❌ No input validation on API endpoints
- ❌ CRITICAL or HIGH security vulnerabilities

---

## Success Criteria

QA is **COMPLETE** when:
- ✅ All automated tests pass
- ✅ Code quality tools show no errors
- ✅ Security scan clean (no Critical/High)
- ✅ Manual testing completed
- ✅ Documentation updated
- ✅ Knowledge base updated
- ✅ Peer review approved (if applicable)

---

*Quality is not an accident; it is the result of systematic checks. This checklist might seem long, but it prevents bugs that take 10x longer to fix in production.*
