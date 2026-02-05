# Quality Checklist Template

**Purpose**: Quick reference checklist for pre-commit quality gates. Print this out or keep it handy.

**When to Use**: Before EVERY commit, PR, or deployment.

---

## Ultra-Quick Checklist (30 seconds)

For when you're absolutely certain everything is fine (but please use full checklist periodically):

```markdown
□ All tests pass
□ No secrets in code
□ Code formatted
□ Documentation updated
```

---

## Standard Checklist (5 minutes)

For most commits:

### Testing
□ All unit tests pass
□ All integration tests pass
□ No tests skipped or disabled
□ No regressions (existing features still work)

### Security
□ No API keys, tokens, passwords in code
□ No secrets in comments
□ Dependencies have no CRITICAL/HIGH vulnerabilities
□ Input validation present at boundaries

### Code Quality
□ Code formatted (black/prettier/gofmt)
□ No linter errors (flake8/eslint)
□ Type check passes (mypy/tsc)
□ Cyclomatic complexity <10

### Documentation
□ README updated (if user-facing change)
□ API docs updated (if API changed)
□ Docstrings added for new functions
□ Comments added for complex logic

### Git
□ Only intended files staged
□ No .env or large binaries staged
□ Commit message clear and descriptive

### Knowledge Base
□ `.claude/state/current-state.md` updated
□ Lessons learned documented (if applicable)

---

## Comprehensive Checklist (15-30 minutes)

For important features, releases, or GitHub preparation:

### 1. Automated Testing

#### Unit Tests
□ All unit tests pass: `pytest tests/unit/ -v`
□ Test coverage >80%: `pytest --cov=core --cov=api`
□ Fast execution (<30 seconds)
□ Tests are deterministic (no flaky tests)

#### Integration Tests
□ All integration tests pass: `pytest tests/integration/ -v`
□ Database migrations tested (if applicable)
□ External API mocks working
□ Error handling tested (not just happy paths)

#### End-to-End Tests
□ Critical user flows work: `pytest tests/e2e/ -v`
□ UI renders correctly (if web app)
□ APIs return correct responses
□ Error messages user-friendly

#### Regression Tests
□ Entire test suite passes: `pytest tests/ -v`
□ No new warnings in logs
□ Performance hasn't degraded
□ Memory usage stable

---

### 2. Code Quality

#### Formatting
□ Code formatted:
  - Python: `black . && isort .`
  - JavaScript: `prettier --write "src/**/*.{js,ts,jsx,tsx}"`
  - Go: `gofmt -w .`
  - Rust: `cargo fmt`

□ Consistent indentation
□ Line length <100-120 characters

#### Linting
□ No lint errors:
  - Python: `flake8 core/ api/ cli/`
  - JavaScript: `eslint "src/**/*.{js,ts}"`
  - Go: `golangci-lint run`
  - Rust: `cargo clippy -- -D warnings`

□ No unused imports or variables
□ No undefined names
□ No code complexity warnings

#### Type Checking
□ Type check passes:
  - Python: `mypy core/ api/ cli/ --strict`
  - TypeScript: `tsc --noEmit`
  - Go: `go vet ./...`

□ All public functions have type annotations
□ No `any` types without justification

#### Complexity
□ Cyclomatic complexity <10 per function
□ Maintainability index >65
□ No functions >50 lines
□ No files >500 lines

---

### 3. Security Review

#### Secrets Scanning
□ No secrets in code:
  ```bash
  gitleaks detect --source . --verbose
  git secrets --scan
  grep -r "API_KEY\|SECRET\|PASSWORD" . --exclude-dir=.git
  ```

□ No API keys, tokens, passwords
□ .env files not committed
□ No hardcoded URLs with credentials
□ Secrets in environment variables

#### Dependency Vulnerabilities
□ No CRITICAL vulnerabilities:
  - Python: `pip-audit && safety check`
  - JavaScript: `npm audit`
  - Go: `govulncheck ./...`
  - Rust: `cargo audit`

□ No HIGH vulnerabilities
□ MEDIUM/LOW documented with mitigation

#### OWASP Top 10
□ **A01: Access Control** - Authorization checked on protected endpoints
□ **A02: Cryptographic Failures** - Passwords hashed, HTTPS used
□ **A03: Injection** - Parameterized queries, sanitized input
□ **A04: Insecure Design** - Rate limiting on auth, security logic server-side
□ **A05: Security Misconfiguration** - Debug mode off, defaults changed
□ **A06: Vulnerable Components** - Dependencies updated (see above)
□ **A07: Auth Failures** - Strong passwords, secure sessions
□ **A08: Data Integrity** - Trusted sources, secure CI/CD
□ **A09: Logging Failures** - Failed logins logged, monitoring active
□ **A10: SSRF** - User URLs validated

#### Static Security Analysis
□ Security scan passes:
  ```bash
  bandit -r core/ api/ cli/ -ll  # Python
  semgrep --config auto .        # Multi-language
  ```

---

### 4. Performance (Optional for Most Commits)

#### Load Testing (for performance-critical features)
□ Handles expected load: `k6 run load-test.js`
□ Response time <200ms (p95)
□ No errors under normal load
□ Memory usage stable
□ CPU usage <80% under load

#### Profiling (if performance issue suspected)
□ Profiled for bottlenecks:
  - Python: `python -m cProfile script.py`
  - Node: `node --prof script.js`

---

### 5. Documentation

#### Code Documentation
□ All public functions have docstrings:
  ```python
  def function(arg: type) -> return_type:
      """Brief description.

      Args:
          arg: Description

      Returns:
          Description

      Raises:
          ErrorType: When it happens
      """
  ```

□ Complex logic has WHY comments (not WHAT)
□ No AI attribution comments
□ No TODO/FIXME (fix or create task)
□ No commented-out code

#### External Documentation
□ README.md updated (new features, changed behavior)
□ README examples tested (copy-paste works)
□ API documentation regenerated (if API changed)
□ CHANGELOG.md updated
□ Migration guide (if breaking changes)

---

### 6. Architecture Compliance

#### API-First Architecture
□ Core logic in `core/` (pure functions, no I/O)
□ API layer in `api/` (thin wrapper around core)
□ UI/CLI in `cli/`or `ui/` (calls API, never core directly)
□ Clear separation of concerns

#### Test-Driven Development
□ Tests written before implementation (or at same time)
□ Tests cover happy paths
□ Tests cover error paths
□ Tests cover edge cases
□ Test coverage >80%

---

### 7. Git & Version Control

#### Git Status
□ `git status` shows only intended changes
□ No .env or secret files staged
□ No large binaries accidentally added
□ .gitignore properly configured

#### Build Success
□ Build completes: `python -m build` / `npm run build`
□ No build errors
□ No build warnings (or documented)

#### Commit Quality
□ Read own diff: `git diff --staged`
□ No debug print statements
□ No hardcoded values (use constants/config)
□ No typos in strings
□ No overly long functions
□ No magic numbers

---

### 8. Knowledge Base Updates

#### State Update
□ `.claude/state/current-state.md` updated:
  - Task status (pending → in_progress → completed)
  - Recent changes section
  - Next steps section

#### Lessons Learned
□ `.claude/knowledge-base/lessons-learned.md` updated:
  - Bugs fixed
  - Gotchas discovered
  - What worked well

#### Tech Stack Decisions
□ `.claude/knowledge-base/tech-stack-decisions.md` updated:
  - New libraries added
  - Technology choices made
  - Rationale documented

---

### 9. Pre-Commit Final Check

#### Manual Testing
□ Run application locally
□ Test new feature manually
□ Test error cases
□ Verify no regressions in related features

#### Review Diff
□ Read entire diff: `git diff --staged`
□ Every change intentional
□ No unrelated changes (scope creep)
□ Consistent style with surrounding code

#### Commit Message
□ Clear and descriptive
□ Explains WHY (not just WHAT)
□ Follows format:
  ```
  [type]: Brief description (max 70 chars)

  Detailed explanation (why this change, impact)

  Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
  ```

---

## Red Flags (STOP and Fix)

If you see any of these, **DO NOT COMMIT** until fixed:

🚫 Tests disabled or commented out
🚫 Secrets in code (even in comments)
🚫 SQL queries with string concatenation
🚫 `eval()` or `exec()` with user input
🚫 `try/except pass` (silent error swallowing)
🚫 Passwords in plaintext or just encrypted
🚫 No input validation on API endpoints
🚫 CRITICAL or HIGH security vulnerabilities
🚫 Breaking changes without migration plan
🚫 Removing functionality without deprecation notice

---

## Checklist for Specific Scenarios

### Before Creating Pull Request
□ All items in "Comprehensive Checklist" above
□ PR description explains what and why
□ Screenshots/videos for UI changes
□ Breaking changes clearly documented
□ Reviewers assigned

### Before Deploying to Production
□ All items in "Comprehensive Checklist" above
□ Staging deployment successful
□ Smoke tests pass on staging
□ Monitoring/alerting configured
□ Rollback plan documented
□ On-call engineer notified (if high-risk)

### Before Making Repository Public (GitHub)
□ No secrets in entire git history: `gitleaks detect`
□ No credentials in any commit
□ README complete and professional
□ LICENSE file present
□ No internal company info in code or docs
□ No large files (>100MB)

---

## Automation Recommendations

### Pre-Commit Hook
Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
set -e
echo "Running pre-commit checks..."
black --check . || exit 1
flake8 core/ api/ cli/ || exit 1
mypy core/ api/ cli/ || exit 1
pytest tests/ -v || exit 1
echo "✅ All checks passed!"
```

### CI/CD Pipeline
Use GitHub Actions, GitLab CI, or similar:
- Run all tests on every push
- Run security scans on every PR
- Block merge if tests fail
- Auto-deploy to staging after merge to main

---

## Time Estimates

- **Ultra-Quick Checklist**: 30 seconds
- **Standard Checklist**: 5 minutes
- **Comprehensive Checklist**: 15-30 minutes
- **GitHub Preparation**: 1-2 hours (first time)

**Note**: Time investment pays off in prevented bugs. A 5-minute checklist prevents 5-hour debugging sessions.

---

## Customization

Edit this checklist for your project:

### Add Project-Specific Checks
```markdown
□ [Your specific requirement]
□ [Your coding standard]
□ [Your deployment step]
```

### Remove Irrelevant Checks
If you don't have a UI, remove UI-related checks. If you don't use Docker, remove container checks.

### Adjust Coverage Targets
```markdown
□ Test coverage >[your target]%
□ Complexity <[your threshold]
```

---

## Success Criteria

Quality check is **COMPLETE** when:
- ✅ All applicable items checked
- ✅ All red flags resolved
- ✅ Commit is production-ready

---

*Quality is a habit, not an accident. Make this checklist second nature.*
