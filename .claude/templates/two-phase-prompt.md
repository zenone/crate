# Two-Phase Prompt Template

**Purpose**: Reusable template for the two-phase workflow (planning → execution) that ensures high-quality implementation with minimal regressions.

**When to Use**: For ANY non-trivial task (feature implementation, refactoring, bug fix that affects multiple files).

---

## How to Use This Template

1. Copy the template below
2. Fill in the `[TASK DESCRIPTION]` section with your specific request
3. Claude will execute Phase 1 (planning) then Phase 2 (implementation)
4. Review the plan before approving execution

---

## Template

```markdown
You are a senior/staff-level software engineer working in an existing production codebase.

IMPORTANT: This is a TWO-PHASE workflow. You must do Phase 1 fully before Phase 2.

PHASE 1 — PROMPT IMPROVEMENT ("Prompt Compiler")
Goal: Rewrite the task prompt into a high-quality, unambiguous, senior-level engineering prompt that will produce correct code with minimal regressions.

Rules for Phase 1:
- Do NOT solve the task yet.
- Produce a rewritten prompt that is:
  - Specific about scope, constraints, and expected behavior
  - Explicit about repo context needed (files, commands, environment)
  - Explicit about acceptance criteria / definition of done
  - Explicit about testing requirements (add/adjust tests; include edge cases)
  - Explicit about "don't break existing code" and "minimal diffs"
- If key details are missing, do NOT ask questions unless truly blocked.
  - Instead, insert a short "Assumptions" section into the rewritten prompt with conservative defaults.
- Keep the rewritten prompt concise but complete.

Output for Phase 1 (exact format):
1) IMPROVED PROMPT (copy-ready, no commentary)
2) ASSUMPTIONS (only if needed; bullet list)

PHASE 2 — EXECUTE THE IMPROVED PROMPT
Now treat the IMPROVED PROMPT you produced in Phase 1 as the ONLY task request, and execute it.

Execution Rules (senior-level quality bar):
- First read relevant files before editing.
- Make minimal, localized changes; avoid unrelated refactors/format churn.
- Add or update tests to protect behavior (TDD preferred when feasible).
- Run or propose exact commands for tests/lint/typecheck/format.
- Provide a final report: what changed, why, tests run, and any remaining risks.

STOP CONDITIONS
- If the IMPROVED PROMPT still cannot be executed due to missing critical info, state exactly what is missing and the smallest set of questions needed. Otherwise proceed.

USER TASK PROMPT (to be improved in Phase 1):
[TASK DESCRIPTION]
```

---

## Example Usage

### Example 1: Feature Request

**Input**:
```
[TASK DESCRIPTION]
Add user authentication with JWT tokens
```

**Phase 1 Output** (Claude generates):
```markdown
IMPROVED PROMPT:
Implement JWT-based user authentication with the following requirements:

Scope:
- Add authentication endpoints: POST /api/v1/login, POST /api/v1/logout
- Implement password hashing with bcrypt
- Generate and validate JWT tokens
- Add authentication middleware for protected routes

Constraints:
- Follow existing API-first architecture (core → api → cli/ui)
- Use existing user model in core/users.py
- Maintain backward compatibility (no breaking changes to existing endpoints)

Expected Behavior:
- Login with valid credentials → Returns JWT token
- Login with invalid credentials → Returns 401
- Protected routes without token → Returns 401
- Protected routes with expired token → Returns 401
- Token expires after 24 hours

Definition of Done:
- Unit tests for hash_password, verify_password, generate_jwt, validate_jwt
- Integration tests for /login endpoint (success + failure cases)
- Authentication middleware tested
- Documentation updated (README, API docs)
- No regressions in existing tests

Testing Requirements:
- Test happy path (correct credentials)
- Test error paths (wrong password, missing fields, malformed token)
- Test edge cases (SQL injection attempts, very long passwords, unicode)
- Test token expiration

Files to Read:
- core/users.py (understand user model)
- api/routes.py (understand existing patterns)
- tests/test_api.py (understand test patterns)

Files to Create/Modify:
- core/auth.py (new: business logic)
- api/routes.py (modify: add /login endpoint)
- api/middleware.py (modify: add auth middleware)
- tests/test_auth.py (new: auth tests)
- tests/test_api.py (modify: test protected endpoints)
- README.md (update: document auth)

ASSUMPTIONS:
- Using bcrypt for password hashing (standard practice)
- JWT stored in httpOnly cookies (more secure than localStorage)
- Token secret will be in environment variable JWT_SECRET
- Rate limiting for login endpoint (5 attempts per minute per IP)
```

**Phase 2**: Claude executes the improved prompt

---

### Example 2: Bug Fix

**Input**:
```
[TASK DESCRIPTION]
Users report that the export feature crashes on large datasets (>1000 rows)
```

**Phase 1 Output** (Claude generates):
```markdown
IMPROVED PROMPT:
Debug and fix crash in export feature when handling large datasets.

Scope:
- Identify root cause of crash for datasets >1000 rows
- Fix the issue without breaking existing functionality
- Add tests to prevent regression

Investigation Steps:
1. Read export feature implementation
2. Check for memory issues (loading entire dataset into memory)
3. Check for timeout issues (long-running operations)
4. Review error logs for stack traces

Expected Root Causes (hypotheses to test):
- Loading entire dataset into memory at once (O(n) memory)
- No pagination or streaming for large results
- Database query timeout
- File handle not closed properly

Definition of Done:
- Root cause identified and documented
- Fix implemented with minimal code changes
- Regression test added (test with 1000+ row dataset)
- All existing tests still pass
- Performance verified (export of 10,000 rows completes successfully)

Testing Requirements:
- Write failing test that reproduces crash (TDD)
- Test with edge cases: 100, 1000, 5000, 10000 rows
- Test memory usage (should not load entire dataset into memory)
- Test existing functionality (small exports still work)

Files to Read:
- [path to export feature]
- [path to database queries]
- [path to file generation]
- tests/test_export.py

Risk Assessment:
- Could affect existing export functionality
- Need to verify performance doesn't degrade for small exports
- Need to ensure file format remains identical

ASSUMPTIONS:
- Export feature is in core/export.py or similar
- Issue is likely memory-related (common for large dataset issues)
- Using Python (will use generators for streaming if needed)
```

**Phase 2**: Claude executes the improved prompt

---

### Example 3: Refactoring

**Input**:
```
[TASK DESCRIPTION]
The auth module has gotten too complex. Refactor it to be more maintainable.
```

**Phase 1 Output** (Claude generates):
```markdown
IMPROVED PROMPT:
Refactor auth module to improve maintainability while preserving all existing functionality.

Scope:
- Split auth.py into smaller, focused modules if >500 lines
- Extract complex functions into helpers
- Improve naming for clarity
- Add type hints if missing
- Add docstrings if missing

Constraints:
- ZERO behavior changes (pure refactoring)
- All existing tests must pass unchanged
- No breaking changes to API (maintain all function signatures)
- No new dependencies

Current State Analysis (to be done):
1. Read core/auth.py
2. Identify:
   - Functions >50 lines (candidates for extraction)
   - Duplicated code (DRY violations)
   - Unclear variable names
   - Missing type hints or docstrings
   - High cyclomatic complexity (>10)

Refactoring Plan (to be generated):
- List specific refactorings needed
- Estimate risk for each change
- Propose new file structure if splitting module

Definition of Done:
- Code complexity reduced (cyclomatic complexity <10 per function)
- No functions >50 lines
- All functions have docstrings and type hints
- No code duplication
- All existing tests pass (100% pass rate)
- No new test failures

Testing Requirements:
- Run full test suite before refactoring (establish baseline)
- Run tests after each refactoring step
- If tests fail, revert that change and try different approach
- Final verification: diff of test output before/after should be empty

Safety Measures:
- Make small, incremental commits
- Run tests after each commit
- Be prepared to revert if tests fail

ASSUMPTIONS:
- Auth module is in core/auth.py
- Existing test coverage is sufficient (won't add new tests, just refactor)
- Team prefers small PRs (will keep changes minimal)
```

**Phase 2**: Claude executes the improved prompt

---

## Phase 1 Prompt Engineering Tips

### Make Scope Explicit
- ✅ "Add authentication endpoint POST /api/v1/login"
- ❌ "Add authentication"

### Make Constraints Explicit
- ✅ "Follow existing API-first architecture (core → api → ui)"
- ❌ "Add it to the project"

### Make Acceptance Criteria Explicit
- ✅ "Login with valid credentials returns JWT token; invalid credentials return 401"
- ❌ "Make login work"

### Make Testing Requirements Explicit
- ✅ "Test happy path, error paths (wrong password, missing fields), edge cases (SQL injection, unicode)"
- ❌ "Add tests"

### Identify Files to Read
- ✅ "Read core/users.py (user model), api/routes.py (patterns)"
- ❌ "Check the codebase"

### Conservative Assumptions
- ✅ "Assuming bcrypt for hashing (industry standard)"
- ❌ "Assuming we'll use the auth library you prefer"

---

## Phase 2 Execution Tips

### Read Before Writing
```python
# ✅ Good
# 1. Read core/users.py
# 2. Understand existing User model
# 3. Write auth code that integrates cleanly

# ❌ Bad
# 1. Write auth code
# 2. Try to integrate
# 3. Realize it doesn't fit existing patterns
# 4. Rewrite everything
```

### Minimal Changes
```python
# ✅ Good: Add auth without touching unrelated code
+ from core.auth import require_auth
+
+ @require_auth
  def protected_route():
      return data

# ❌ Bad: Refactor unrelated code while adding auth
- def protected_route():
-     return data
+ def protected_route():
+     """Protected route (requires authentication)."""
+     result = process_data()
+     return result
+
+ def process_data():
+     # Extracted helper (unrelated refactoring)
+     return data
```

### Test After Every Change
```bash
# ✅ Good
git add core/auth.py
pytest tests/test_auth.py  # Passes
git commit -m "Add password hashing"

git add api/routes.py
pytest tests/  # Passes
git commit -m "Add /login endpoint"

# ❌ Bad
# Make 10 changes
pytest tests/  # Fails
# Now debug which of 10 changes broke it
```

---

## Common Pitfalls

### ❌ Skipping Phase 1
**Problem**: Start implementing immediately without planning

**Result**: Build wrong thing, miss edge cases, need to rewrite

**Solution**: Always do Phase 1, even for "simple" tasks

---

### ❌ Vague Phase 1 Prompt
**Problem**: Phase 1 output still ambiguous ("add feature X")

**Result**: Phase 2 makes assumptions that turn out wrong

**Solution**: Phase 1 should be so specific that Phase 2 is mechanical

---

### ❌ Not Reading Existing Code
**Problem**: Write code without understanding existing patterns

**Result**: Inconsistent code style, breaks assumptions, duplicates logic

**Solution**: Phase 1 should explicitly list files to read

---

### ❌ Large Scope in Single Task
**Problem**: Try to implement entire feature in one go

**Result**: Large PR, hard to review, many potential break points

**Solution**: Break into smaller tasks, each with own two-phase workflow

---

### ❌ Skipping Tests in Phase 2
**Problem**: "I'll add tests later"

**Result**: Tests never added, or tests are afterthought (only test happy path)

**Solution**: Phase 1 should mandate TDD (tests first)

---

## Customization for Your Project

Edit this template based on your project's needs:

### Add Project-Specific Constraints
```markdown
Constraints:
- Follow existing API-first architecture (core → api → ui)
- Use existing [YOUR_FRAMEWORK] patterns
- Maintain [YOUR_CODING_STANDARD]
- [YOUR_SPECIFIC_CONSTRAINT]
```

### Add Project-Specific Testing Requirements
```markdown
Testing Requirements:
- Unit tests (pytest)
- Integration tests (pytest-integration)
- [YOUR_SPECIFIC_TEST_TYPE]
- Coverage >80%
```

### Add Project-Specific Definition of Done
```markdown
Definition of Done:
- Code review approved
- Documentation updated
- [YOUR_SPECIFIC_REQUIREMENT]
- Deployed to staging
```

---

## Quick Reference

**When to use two-phase workflow**:
- ✅ Implementing new feature
- ✅ Fixing complex bug (multiple files affected)
- ✅ Refactoring (>100 lines changed)
- ✅ Architecture changes
- ❌ Typo fixes
- ❌ Trivial updates (change one constant)

**Phase 1 should answer**:
- What exactly are we building?
- Which files will we touch?
- What could go wrong?
- How will we test it?
- What does "done" mean?

**Phase 2 should deliver**:
- Working code
- Passing tests
- Updated documentation
- Commit-ready changes

---

*The two-phase workflow transforms vague requests into precise specifications, then executes those specifications with surgical precision. Use it religiously for quality.*
