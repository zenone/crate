# Feature Development Workflow

**Purpose**: Step-by-step process for implementing any new feature with high quality and minimal regressions.

---

## Prerequisites

Before starting ANY feature:
- [ ] Read `.claude/state/current-state.md`
- [ ] Review `.claude/knowledge-base/lessons-learned.md`
- [ ] Check `.claude/knowledge-base/tech-stack-decisions.md`
- [ ] Verify all existing tests pass
- [ ] Ensure working directory is clean (no uncommitted changes)

---

## Phase 1: Planning & Design (Don't Skip This!)

### Step 1: Clarify Requirements (5-10 min)

**Goal**: Ensure you understand what's being asked before writing any code.

**Questions to Answer**:
1. What problem does this feature solve?
2. Who is the user and what's their use case?
3. What does success look like? (Definition of Done)
4. Are there edge cases or error conditions?
5. What should happen if this feature fails?

**Output**: Written specification (can be brief, but must be explicit)

**Example**:
```markdown
Feature: User Authentication with JWT

Problem: Users need secure way to access protected resources
User: Any application user (authenticated access required)
Success: User can login, receive JWT, use token for API calls
Edge Cases:
- Invalid credentials
- Expired token
- Token refresh
- Concurrent sessions
Failure Mode: Graceful error message, no data exposure
```

---

### Step 2: Research Best Practices (10-15 min)

**Goal**: Learn current best practices before implementing (avoid reinventing wheel).

**Web Search Queries**:
```
"[feature name] best practices 2026"
"[feature name] security vulnerabilities"
"[feature name] [your language/framework] implementation"
"[feature name] vs [alternative approach]"
```

**Check**:
- Official documentation for libraries you'll use
- Stack Overflow for common pitfalls
- GitHub for example implementations
- Security advisories (CVEs related to this feature)

**Output**: Document findings in `.claude/knowledge-base/tech-stack-decisions.md` if choosing libraries

---

### Step 3: Design API Contract (API-First Architecture)

**Goal**: Define the interface before implementation.

**For Every Feature, Define**:
1. **Endpoints** (if web API):
   - Method: GET/POST/PUT/DELETE
   - Path: `/api/v1/resource`
   - Request format: JSON schema or TypeScript types
   - Response format: JSON schema or TypeScript types
   - Status codes: 200, 400, 401, 500, etc.

2. **Function Signatures** (if library/CLI):
   - Function name and parameters
   - Return type
   - Exceptions/errors thrown

3. **OpenAPI Spec** (recommended):
   ```yaml
   /api/v1/login:
     post:
       summary: User login
       requestBody:
         required: true
         content:
           application/json:
             schema:
               type: object
               properties:
                 username: {type: string}
                 password: {type: string}
       responses:
         200:
           description: Success
           content:
             application/json:
               schema:
                 type: object
                 properties:
                   token: {type: string}
         401:
           description: Invalid credentials
   ```

**Output**: API contract document (can be in code comments if simple)

---

### Step 4: Identify Affected Code Paths

**Goal**: Know what you'll need to change BEFORE changing it.

**Questions**:
1. What files will this feature touch?
2. Are there existing functions that do something similar?
3. Will this break any existing features?
4. Are there tests that will need updating?
5. Are there multiple code paths (web + CLI + API)?

**Output**: List of files to modify/create

**Example**:
```
Files to Change:
- core/auth.py (new functions: hash_password, verify_token)
- api/routes.py (new endpoint: POST /login)
- tests/test_auth.py (new tests for auth functions)
- tests/test_api.py (new tests for login endpoint)

Files to Read:
- core/users.py (existing user model)
- api/middleware.py (existing auth middleware)
```

---

### Step 5: Risk Assessment

**Goal**: Identify what could go wrong BEFORE it goes wrong.

**Check For**:
1. **Race Conditions**: Could this run before dependencies are ready?
2. **Breaking Changes**: Will this affect existing features?
3. **Security Risks**: Could this introduce vulnerabilities?
4. **Performance Impact**: Will this slow down critical paths?
5. **Data Integrity**: Could this corrupt or lose data?
6. **Timing Issues**: Is initialization order correct?

**Output**: Risk mitigation plan

**Example**:
```
Risks:
1. Storing passwords in plaintext → Use bcrypt hashing
2. JWT tokens never expire → Implement expiration + refresh
3. Token stored in localStorage (XSS risk) → Use httpOnly cookies
4. Brute force attacks → Implement rate limiting
```

---

### Step 6: Get Approval (if working with human)

**Present**:
- Requirements (what you understood)
- API design (how it will work)
- Files affected (what will change)
- Risks identified (what could go wrong)
- Estimated scope (how many files/tests)

**Get explicit "go ahead" before Phase 2**

---

## Phase 2: Test-Driven Implementation

### Step 7: Write Failing Tests First (TDD - RED)

**Goal**: Prove the feature doesn't exist yet, and define expected behavior.

**Test Types to Write**:
1. **Unit Tests** (core business logic):
   ```python
   def test_hash_password_returns_different_hash_each_time():
       password = "secret123"
       hash1 = hash_password(password)
       hash2 = hash_password(password)
       assert hash1 != hash2  # Should use salt

   def test_verify_password_accepts_correct_password():
       password = "secret123"
       hashed = hash_password(password)
       assert verify_password(password, hashed) is True

   def test_verify_password_rejects_wrong_password():
       hashed = hash_password("secret123")
       assert verify_password("wrong", hashed) is False
   ```

2. **Integration Tests** (API endpoints):
   ```python
   def test_login_endpoint_returns_token_on_valid_credentials():
       response = client.post("/api/v1/login", json={
           "username": "testuser",
           "password": "correctpassword"
       })
       assert response.status_code == 200
       assert "token" in response.json()

   def test_login_endpoint_returns_401_on_invalid_credentials():
       response = client.post("/api/v1/login", json={
           "username": "testuser",
           "password": "wrongpassword"
       })
       assert response.status_code == 401
   ```

3. **Edge Case Tests**:
   ```python
   def test_login_with_missing_username():
       response = client.post("/api/v1/login", json={"password": "test"})
       assert response.status_code == 400

   def test_login_with_sql_injection_attempt():
       response = client.post("/api/v1/login", json={
           "username": "admin' OR '1'='1",
           "password": "anything"
       })
       assert response.status_code == 401  # Should reject, not crash
   ```

**Run Tests**: They should ALL FAIL (RED state)

**Output**: Comprehensive test suite (failing)

---

### Step 8: Implement Core Logic (Minimum to Pass Tests)

**Goal**: Write simplest code that makes tests pass.

**Implementation Order**:
1. **Core business logic first** (`core/` directory):
   - Pure functions
   - No I/O, no framework dependencies
   - Testable in isolation

2. **API layer second** (`api/` directory):
   - Thin wrapper around core logic
   - Input validation
   - Error handling
   - Response formatting

3. **UI/CLI last** (`ui/` or `cli/` directory):
   - Calls API (never calls core directly)
   - Presentation logic only
   - User interaction handling

**Code Quality Rules**:
- Descriptive variable names (no abbreviations unless standard)
- Comments only for non-obvious logic
- Type hints (Python) or TypeScript
- Defensive error handling
- Debug logging (removable via flag)

**Example Structure**:
```python
# core/auth.py (business logic)
def hash_password(password: str) -> str:
    """Hash password using bcrypt with automatic salt generation."""
    import bcrypt
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    import bcrypt
    return bcrypt.checkpw(password.encode(), hashed.encode())

# api/routes.py (API layer)
from core.auth import verify_password
from core.users import get_user_by_username

@app.post("/api/v1/login")
def login(username: str, password: str):
    """Authenticate user and return JWT token."""
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = generate_jwt(user.id)
    return {"token": token}

# cli/main.py (CLI interface - calls API)
def cmd_login(username: str, password: str):
    """Login command (calls API)."""
    response = api_client.post("/api/v1/login", json={
        "username": username,
        "password": password
    })
    if response.status_code == 200:
        save_token(response.json()["token"])
        print("Login successful!")
    else:
        print("Login failed:", response.json()["detail"])
```

**Run Tests**: They should pass (GREEN state)

---

### Step 9: Refactor (Keep Tests Green)

**Goal**: Improve code quality without changing behavior.

**Refactoring Checklist**:
- [ ] Remove duplication (DRY principle)
- [ ] Extract complex logic into helper functions
- [ ] Improve variable names
- [ ] Add type hints if missing
- [ ] Add docstrings for public functions
- [ ] Remove debug print statements (use logging instead)
- [ ] Check code style (PEP-8 for Python, ESLint for JS)

**Run Tests After Every Change**: Must stay GREEN

**What NOT to Refactor**:
- Don't refactor code you didn't touch (scope creep)
- Don't "improve" working code just because (YAGNI)
- Don't add abstractions for one use case

---

### Step 10: Security Review

**Goal**: Ensure no vulnerabilities introduced.

**Security Checklist**:
- [ ] No secrets in code (API keys, passwords, tokens)
- [ ] Input validation at all boundaries (API, CLI)
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (escape output)
- [ ] CSRF protection (if web app)
- [ ] Authentication required where needed
- [ ] Authorization checked (user can access this resource?)
- [ ] Rate limiting (prevent brute force)
- [ ] Error messages don't leak sensitive info
- [ ] Dependencies have no known CVEs

**Run Security Tools** (if available):
```bash
# Python example
bandit -r core/ api/
safety check
```

**If Critical or High Vulns Found**: Stop and fix before proceeding

---

### Step 11: Integration Testing

**Goal**: Verify feature works end-to-end, not just in isolation.

**Integration Test Scenarios**:
1. Happy path (everything works)
2. Error paths (things go wrong)
3. Edge cases (boundary conditions)
4. Concurrent usage (if applicable)
5. Integration with existing features

**Example Integration Test**:
```python
def test_full_user_authentication_flow():
    # Create user
    response = client.post("/api/v1/register", json={
        "username": "newuser",
        "password": "secure123"
    })
    assert response.status_code == 201

    # Login
    response = client.post("/api/v1/login", json={
        "username": "newuser",
        "password": "secure123"
    })
    assert response.status_code == 200
    token = response.json()["token"]

    # Access protected resource
    response = client.get("/api/v1/profile", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    assert response.json()["username"] == "newuser"
```

**Run Full Test Suite**: All tests (unit + integration) must pass

---

### Step 12: Manual Testing

**Goal**: Test as a real user would use it.

**Manual Test Cases**:
1. Test via API (Postman, curl, or HTTP client)
2. Test via CLI (if applicable)
3. Test via UI (if applicable)
4. Test error cases (wrong input, missing auth, etc.)
5. Test on different environments (dev, staging)

**Example Manual Tests**:
```bash
# Test login API
curl -X POST http://localhost:8000/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "test123"}'

# Expected: {"token": "eyJ..."}

# Test with wrong password
curl -X POST http://localhost:8000/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "wrong"}'

# Expected: 401 {"detail": "Invalid credentials"}
```

**Document Any Issues Found**: Add to `.claude/knowledge-base/lessons-learned.md`

---

## Phase 3: Quality Assurance & Documentation

### Step 13: Regression Testing

**Goal**: Ensure feature didn't break existing functionality.

**Regression Checklist**:
- [ ] Run entire test suite (not just new tests)
- [ ] Test existing features manually
- [ ] Check for performance degradation
- [ ] Verify no new warnings/errors in logs

**If Regressions Found**:
1. Write test that reproduces regression
2. Fix regression
3. Verify all tests pass
4. Document in lessons-learned.md

---

### Step 14: Code Quality Check

**Goal**: Ensure code meets project standards.

**Quality Checklist**:
- [ ] All functions have docstrings
- [ ] Complex logic has comments
- [ ] No TODO or FIXME comments (fix or create task)
- [ ] No commented-out code (delete it, git remembers)
- [ ] No AI attribution comments ("Generated by Claude")
- [ ] Code style consistent (run formatter)
- [ ] No unused imports or variables
- [ ] Type hints present (if applicable)

**Run Quality Tools**:
```bash
# Python example
black .                    # Format code
flake8 core/ api/         # Lint
mypy core/ api/           # Type check
pylint core/ api/         # Quality check
```

---

### Step 15: Update Documentation

**Goal**: Future you (and your team) understands this feature.

**Documentation Updates**:
1. **README.md** (if user-facing feature):
   - Add feature to features list
   - Add usage example
   - Update installation steps if needed

2. **API Documentation** (if API changed):
   - Update OpenAPI spec
   - Regenerate API docs
   - Add example requests/responses

3. **Inline Comments** (for complex logic):
   - Explain WHY, not WHAT
   - Focus on non-obvious decisions

4. **`.claude/knowledge-base/tech-stack-decisions.md`** (if chose libraries):
   - Document why you chose library X over Y

5. **`.claude/state/current-state.md`**:
   - Update "Recent Changes" section
   - Update "Next Steps"

**Example README Update**:
```markdown
## Features

- **User Authentication**: Secure JWT-based authentication
  ```bash
  # Login
  curl -X POST http://localhost:8000/api/v1/login \
    -H "Content-Type: application/json" \
    -d '{"username": "user", "password": "pass"}'

  # Use token
  curl http://localhost:8000/api/v1/profile \
    -H "Authorization: Bearer <token>"
  ```
```

---

### Step 16: Update Knowledge Base

**Goal**: Capture lessons for future features.

**Update Files**:

1. **`.claude/knowledge-base/lessons-learned.md`**:
   - What went well?
   - What went wrong?
   - What would you do differently?
   - Any gotchas or surprising behavior?

2. **`.claude/state/current-state.md`**:
   - Move task from "In Progress" to "Completed"
   - Update "Recent Changes" section
   - Add "Next Steps"

**Example Lesson**:
```markdown
## [2026-02-01] JWT Authentication Implementation

**Context**: Implementing user authentication

**Problem**: Initially stored JWT in localStorage (XSS vulnerability)

**Solution**: Changed to httpOnly cookies

**Prevention**: Always research security best practices before implementing auth

**Tags**: #security #authentication
```

---

## Phase 4: Commit & Deploy

### Step 17: Pre-Commit Checklist

**Goal**: Ensure commit is production-ready.

**Final Checklist**:
- [ ] All tests pass (unit + integration)
- [ ] No regressions in existing features
- [ ] Code formatted and linted
- [ ] Documentation updated
- [ ] No secrets in code
- [ ] No debug logging (or controlled by flag)
- [ ] `.claude/state/current-state.md` updated
- [ ] `.claude/knowledge-base/lessons-learned.md` updated if learned something

**If Any Item Fails**: Fix before committing

---

### Step 18: Git Commit

**Goal**: Create clear, atomic commit.

**Commit Message Format**:
```
[Type]: Brief description (max 70 chars)

- Detailed explanation (why, not what)
- Impact on users or system
- Related issues or decisions

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Types**: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

**Example**:
```
feat: Add JWT-based user authentication

- Implements secure password hashing with bcrypt
- Adds /api/v1/login endpoint returning JWT tokens
- Includes rate limiting to prevent brute force attacks
- Tokens expire after 24 hours with refresh mechanism

Addresses security requirement from issue #42

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Commit**:
```bash
git add core/auth.py api/routes.py tests/
git commit -m "$(cat <<'EOF'
feat: Add JWT-based user authentication

- Implements secure password hashing with bcrypt
- Adds /api/v1/login endpoint returning JWT tokens
- Includes rate limiting to prevent brute force attacks
- Tokens expire after 24 hours with refresh mechanism

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Step 19: Deploy (if applicable)

**Goal**: Get feature to production safely.

**Deployment Checklist**:
- [ ] Feature flag enabled (for easy rollback)
- [ ] Staging deployment successful
- [ ] Staging tests pass
- [ ] Monitoring/alerting in place
- [ ] Rollback plan documented
- [ ] On-call engineer notified (if high-risk)

**Deployment Steps** (example):
```bash
# Deploy to staging
./deploy.sh staging

# Run smoke tests
./smoke-tests.sh staging

# Deploy to production
./deploy.sh production

# Monitor for 15 minutes
watch -n 60 './check-health.sh'
```

**If Issues Found**: Rollback immediately, fix, redeploy

---

## Common Pitfalls

### ❌ Don't Do This

1. **Skipping Planning Phase**:
   - Problem: Start coding immediately without understanding requirements
   - Result: Implement wrong thing, need to rewrite

2. **Writing Implementation Before Tests**:
   - Problem: Tests become afterthought, only test happy path
   - Result: Bugs in production, low confidence in changes

3. **Implementing Multiple Features at Once**:
   - Problem: Large PR, hard to review, many changes at once
   - Result: Regressions hard to track, rollback affects multiple features

4. **Not Reading Affected Files First**:
   - Problem: Make changes without understanding existing patterns
   - Result: Inconsistent code style, break existing assumptions

5. **Skipping Manual Testing**:
   - Problem: Trust automated tests completely
   - Result: UX issues not caught by tests (wrong error messages, poor flow)

6. **Not Updating Documentation**:
   - Problem: "I'll remember" or "it's obvious"
   - Result: Future confusion, repeated questions, onboarding difficulties

7. **Committing Without Quality Checks**:
   - Problem: "I'll fix it later"
   - Result: Technical debt accumulates, broken main branch

---

## Success Criteria

A feature is **DONE** when:
- ✅ All tests pass (unit, integration, regression)
- ✅ Code reviewed and approved (if applicable)
- ✅ Documentation updated (README, API docs, inline comments)
- ✅ No regressions in existing features
- ✅ Security review passed
- ✅ Manual testing completed
- ✅ Knowledge base updated (lessons learned, current state)
- ✅ Committed with clear message
- ✅ Deployed (if applicable)

---

## Time Estimates (Rough Guidelines)

- Small feature (single function): 1-2 hours
- Medium feature (new API endpoint): 3-6 hours
- Large feature (new subsystem): 1-3 days
- Epic (major new capability): 1-2 weeks

**Note**: These are rough estimates. Don't provide time estimates to users.

---

## Quick Reference Checklist

Copy this for each feature:

```markdown
Feature: [Name]

Phase 1: Planning
- [ ] Requirements clarified
- [ ] Best practices researched
- [ ] API contract designed
- [ ] Affected code paths identified
- [ ] Risks assessed
- [ ] Approval received

Phase 2: Implementation
- [ ] Tests written (failing - RED)
- [ ] Core logic implemented (tests pass - GREEN)
- [ ] Code refactored (tests still pass)
- [ ] Security review passed
- [ ] Integration tests pass
- [ ] Manual testing completed

Phase 3: Quality & Documentation
- [ ] Regression tests pass
- [ ] Code quality checks pass
- [ ] Documentation updated
- [ ] Knowledge base updated

Phase 4: Commit & Deploy
- [ ] Pre-commit checklist complete
- [ ] Git commit with clear message
- [ ] Deployed (if applicable)
```

---

*This workflow should become second nature. The time spent planning saves 10x the time debugging later.*
