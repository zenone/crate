# Dead Code Detection

## Why Remove Dead Code

- Reduces cognitive load
- Shrinks attack surface
- Speeds up tests and builds
- Makes codebase easier to navigate
- Prevents "zombie code" from being accidentally resurrected

## Detection Tools

### Python

**Vulture** (recommended):
```bash
pip install vulture
vulture src/ --min-confidence 80
```

**Coverage with dead code detection**:
```bash
pip install coverage
coverage run -m pytest
coverage report --show-missing
# Functions with 0% coverage are candidates for removal
```

**Ruff (unused imports)**:
```bash
ruff check src/ --select F401,F841
# F401: unused import
# F841: unused variable
```

### JavaScript/TypeScript

**ESLint unused rules**:
```bash
npx eslint . --rule 'no-unused-vars: error' --rule '@typescript-eslint/no-unused-vars: error'
```

**ts-prune**:
```bash
npx ts-prune
```

### General

**grep for suspicious patterns**:
```bash
# Functions defined but never called (rough heuristic)
grep -rn "def " src/ | cut -d: -f2 | while read func; do
    name=$(echo $func | sed 's/def \([a-z_]*\).*/\1/')
    count=$(grep -rn "$name" src/ | wc -l)
    if [ $count -lt 2 ]; then
        echo "Possibly unused: $name"
    fi
done
```

## Safe Removal Process

### Step 1: Identify Candidates
```bash
vulture src/ --min-confidence 80 > dead_code_candidates.txt
```

### Step 2: Verify Each Candidate

Before removing, check:
- [ ] Not called via string/reflection (`getattr`, `eval`)
- [ ] Not exported in `__all__`
- [ ] Not used by external consumers (public API)
- [ ] Not a test fixture or hook
- [ ] Not a CLI entry point

### Step 3: Remove One at a Time
```bash
# Remove one function
# Run tests
pytest tests/ -v
# If tests pass, commit
git commit -m "chore: Remove unused function foo()"
# Repeat
```

### Step 4: Grep for References

After removal, verify no lingering references:
```bash
grep -rn "function_name" .
```

## False Positives

Dead code detectors often flag:
- **Test fixtures**: Used by pytest but not explicitly called
- **Magic methods**: `__init__`, `__str__`, etc.
- **Framework hooks**: Django signals, FastAPI dependencies
- **Exported APIs**: Functions meant for external use
- **Conditional imports**: `if TYPE_CHECKING:`

Always **verify manually** before removing.

## Automation

Add to CI/CD:
```yaml
# .github/workflows/ci.yml
- name: Check for dead code
  run: |
    pip install vulture
    vulture src/ --min-confidence 90
```

Use high confidence (90%) in CI to reduce false positives.

## Anti-Pattern: Commenting Out Code

❌ **Don't do this**:
```python
# def old_implementation():
#     # This was the old way
#     pass
```

✅ **Do this instead**:
```bash
git rm file_with_old_code.py
git commit -m "Remove old implementation (see commit abc123 for history)"
```

Git is your history. Don't keep dead code as comments.
