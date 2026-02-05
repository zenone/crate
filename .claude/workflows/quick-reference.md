# Quick Reference

One-page cheat sheet for daily development. For details, see full workflow docs.

---

## Feature Development (TL;DR)

```
1. PLAN    → Clarify requirements, design API, identify risks
2. TEST    → Write failing tests (TDD red)
3. BUILD   → Implement minimum to pass (TDD green)
4. CLEAN   → Refactor while green
5. VERIFY  → Security review, manual test
6. SHIP    → Update docs, commit, deploy
```

**Kill feature rule**: 3+ debug sessions without resolution → cut it

---

## Git Commit Format

```
<type>: <description>

[optional body]

Co-Authored-By: Claude <noreply@anthropic.com>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

---

## Testing Checklist

- [ ] Tests written BEFORE implementation
- [ ] Happy path covered
- [ ] Edge cases covered (empty, null, boundary)
- [ ] Error cases covered
- [ ] All tests pass: `make test`

---

## Pre-Commit Checklist

- [ ] All tests pass
- [ ] Code formatted: `make fmt`
- [ ] Types check: `make typecheck`
- [ ] No secrets in code
- [ ] Docs updated if needed
- [ ] CHANGELOG updated if releasing

---

## Version Bumping

| Change Type      | Bump  | Example         |
|------------------|-------|-----------------|
| Breaking change  | MAJOR | 1.0.0 → 2.0.0   |
| New feature      | MINOR | 1.0.0 → 1.1.0   |
| Bug fix          | PATCH | 1.0.0 → 1.0.1   |

---

## Fresh Clone Test

```bash
git clone <repo> /tmp/test && cd /tmp/test
make install && make test && make run
rm -rf /tmp/test
```

---

## Error Handling

```python
# Good error message
raise ValidationError(
    f"[Auth] Invalid email format: '{email}'. "
    f"Fix: Use format user@domain.com"
)
```

---

## API-First Architecture

```
api/   → Business logic (import this)
web/   → Web UI (calls api/)
cli/   → CLI (calls api/)
core/  → Utilities (only api/ imports this)
```

---

## Context Management (Claude Code)

- Exit at **75-80%** context utilization
- Use `/clear` between unrelated tasks
- Use subagents for research
- "Think hard" for complex decisions

---

## Common Commands

```bash
make test        # Run tests
make fmt         # Format code
make typecheck   # Type checking
make run         # Start app
make clean       # Clean build artifacts
```
