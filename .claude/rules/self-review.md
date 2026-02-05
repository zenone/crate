# Self-Review Rules

## The Feedback Loop (Critical)

After writing code, **review it yourself AND apply fixes before presenting**. This is not optional.

```
Write Code → Self-Review → Apply Fixes → Re-Review (if needed) → Present
```

**Do NOT** present code for review and then wait for human feedback on issues you could have caught yourself.

## Self-Review Checklist

After writing any significant code, evaluate against these dimensions and **fix issues before proceeding**:

### 1. Code Quality & Best Practices
- [ ] Follows project conventions (check existing code patterns)
- [ ] No magic numbers (use named constants)
- [ ] No unnecessary complexity (simplify if possible)
- [ ] DRY violations eliminated (extract shared logic)
- [ ] Functions < 50 lines, files < 500 lines
- [ ] Descriptive names (no abbreviations unless standard)

### 2. Performance Implications
- [ ] No N+1 queries (batch database calls)
- [ ] No unnecessary loops (can be vectorized?)
- [ ] Large data handled in chunks (not all in memory)
- [ ] Caching considered for expensive operations
- [ ] Async used for I/O-bound operations

### 3. Security Vulnerabilities
- [ ] Input validated at boundaries
- [ ] SQL parameterized (no string concatenation)
- [ ] Secrets not hardcoded (use env vars)
- [ ] Output escaped (XSS prevention)
- [ ] Errors don't leak sensitive info
- [ ] Auth/authz checked on protected paths

### 4. Test Coverage
- [ ] Happy path tested
- [ ] Error paths tested  
- [ ] Edge cases tested (empty, null, boundary values)
- [ ] Tests are deterministic (no flaky tests)

### 5. Documentation
- [ ] Public functions have docstrings
- [ ] Complex logic has "why" comments
- [ ] No TODO/FIXME comments (fix or create task)
- [ ] README updated if user-facing change

### 6. Architectural Concerns
- [ ] Follows API-first pattern (core → api → ui)
- [ ] No circular dependencies
- [ ] Separation of concerns maintained
- [ ] Change is cohesive (not mixing unrelated concerns)

### 7. Maintainability
- [ ] Future developer can understand this (including future-you)
- [ ] Error messages actionable
- [ ] Logging at appropriate levels
- [ ] Configuration externalized (not hardcoded)

## Severity Classification

When issues are found, classify and prioritize:

| Severity | Action | Examples |
|----------|--------|----------|
| **Critical** | Fix immediately | Security vuln, data loss risk, crash |
| **High** | Fix before commit | Bug, missing validation, test failure |
| **Medium** | Fix if time allows | Code smell, minor inefficiency |
| **Low** | Document for later | Style preference, minor naming |

**Rule**: Never commit with Critical or High issues. Medium is judgment call. Low can be noted for future.

## Applying Fixes

When you find an issue:
1. **State the issue** (what's wrong)
2. **Explain severity** (why it matters)
3. **Apply the fix** (don't just recommend—do it)
4. **Verify the fix** (run tests, check it works)

**Example**:
```
Self-Review Finding:
- Issue: SQL query uses string concatenation (Line 42)
- Severity: Critical (SQL injection vulnerability)
- Fix Applied: Changed to parameterized query
- Verification: Tests still pass, tried injection payload in manual test
```

## When to Involve Human

Self-review can't catch everything. Escalate to human review for:
- Security-critical paths (auth, payments, data access)
- Architecture decisions with long-term implications
- Tradeoffs where business context matters
- Anything you're uncertain about

## Integration with Development Workflow

This rule integrates with existing workflows:

1. **feature-development.md Step 9 (Refactor)**: Self-review happens here
2. **quality-assurance.md**: Self-review is the first pass; QA workflow is the comprehensive second pass
3. **git.md**: Self-review must pass before commit

## Anti-Pattern: Review Theater

❌ **Don't do this**:
```
"Here's the code. Issues I noticed:
1. Could use better error handling
2. Missing some edge case tests
3. Magic number on line 15

What do you think?"
```

This puts burden on human to decide what to fix.

✅ **Do this instead**:
```
"Here's the code. During self-review I found and fixed:
1. Added try/catch with specific error handling
2. Added tests for empty input and max boundary
3. Extracted magic number to CONFIG_TIMEOUT constant

All tests pass. Ready for human review of architecture decisions."
```
