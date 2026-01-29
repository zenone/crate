# B2: Type Hints Verification Checklist

**Status**: Ready to Verify
**Date**: 2026-01-28
**Estimated Time**: 30 minutes - 1 hour

---

## VERIFICATION STEPS

### Step 1: Install mypy
```bash
# Option A: Install from requirements-dev.txt
pip3 install -r requirements-dev.txt

# Option B: Install mypy directly
pip3 install mypy>=1.4.0
```

### Step 2: Run mypy strict check
```bash
# Full strict check
mypy dj_mp3_renamer/ --strict

# Show error codes (helpful for debugging)
mypy dj_mp3_renamer/ --strict --show-error-codes

# Generate HTML report
mypy dj_mp3_renamer/ --strict --html-report mypy-report
```

### Step 3: Review Results

**Expected Outcome**:
- **Best case**: 0 errors (type hints are complete)
- **Likely case**: 5-15 minor errors (missing hints in edge cases)
- **Worst case**: 50+ errors (need systematic addition)

### Step 4: Fix Any Issues

**Common Issues & Fixes**:

#### Issue: Missing return type
```python
# Before
def my_function(x: int):
    return x * 2

# After
def my_function(x: int) -> int:
    return x * 2
```

#### Issue: Missing parameter types
```python
# Before
def process(data):
    return data.upper()

# After
def process(data: str) -> str:
    return data.upper()
```

#### Issue: Optional types
```python
# Before
def get_user(id: int):
    # May return None
    pass

# After
from typing import Optional
def get_user(id: int) -> Optional[User]:
    # May return None
    pass
```

#### Issue: Complex types
```python
# Before
def parse_config(config):
    pass

# After
from typing import Dict, Any
def parse_config(config: Dict[str, Any]) -> Dict[str, str]:
    pass
```

#### Issue: Callable types
```python
# Before
def run_callback(callback, value):
    return callback(value)

# After
from typing import Callable
def run_callback(callback: Callable[[int], str], value: int) -> str:
    return callback(value)
```

### Step 5: Verify Tests Still Pass
```bash
# Run all tests
pytest tests/ -v

# Verify count
# Expected: 162 passed
```

### Step 6: Update Documentation
```bash
# If you added significant type hints, update:
- README.md (mention type safety)
- CHANGELOG.md (add type hints entry)
- .claude/TASKS.md (mark B2 complete)
```

---

## MODULES TO CHECK

### High Priority (Core API)
- [ ] `dj_mp3_renamer/api/renamer.py` - Main API class
- [ ] `dj_mp3_renamer/api/models.py` - Data models
- [ ] `dj_mp3_renamer/core/audio_analysis.py` - Audio processing
- [ ] `dj_mp3_renamer/core/io.py` - File operations

### Medium Priority (Core Modules)
- [ ] `dj_mp3_renamer/core/config.py` - Configuration
- [ ] `dj_mp3_renamer/core/validation.py` - Validation functions
- [ ] `dj_mp3_renamer/core/conflict_resolution.py` - Conflict resolution
- [ ] `dj_mp3_renamer/core/metadata_parsing.py` - Metadata parsing
- [ ] `dj_mp3_renamer/core/key_conversion.py` - Key conversion
- [ ] `dj_mp3_renamer/core/template.py` - Template expansion
- [ ] `dj_mp3_renamer/core/sanitization.py` - Filename sanitization

### Low Priority (UI Layer)
- [ ] `dj_mp3_renamer/tui/app.py` - TUI (optional, will be replaced by web UI)
- [ ] `dj_mp3_renamer/cli/main.py` - CLI (thin wrapper)

---

## MYPY CONFIGURATION

Current config in `pyproject.toml`:
```toml
[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # Set to true when ready
```

**Recommended changes for strict mode**:
```toml
[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true        # Enable for strict
check_untyped_defs = true           # Check even untyped functions
disallow_any_generics = true        # Require specific generics
disallow_incomplete_defs = true     # All params must be typed
disallow_untyped_calls = false      # Too strict for libraries
warn_redundant_casts = true         # Warn about unnecessary casts
warn_unused_ignores = true          # Warn about unused type: ignore
```

---

## SUCCESS CRITERIA

- [ ] `mypy dj_mp3_renamer/ --strict` returns 0 errors
- [ ] All 162 tests pass
- [ ] No use of `# type: ignore` except where documented
- [ ] IDE auto-complete works in VS Code/PyCharm
- [ ] Type hints are accurate (not just `Any` everywhere)

---

## ESTIMATED ISSUES BY MODULE

Based on code review:

| Module | Estimated Issues | Priority |
|--------|-----------------|----------|
| `core/audio_analysis.py` | 0-5 (mostly typed) | High |
| `api/renamer.py` | 0-3 (appears typed) | High |
| `core/io.py` | 0-2 (appears typed) | High |
| `core/config.py` | 0-3 | Medium |
| `core/validation.py` | 0-2 | Medium |
| Other core modules | 0-10 total | Medium |
| UI layers | 10-20 (not critical) | Low |

**Total Estimated**: 0-30 errors (manageable)

---

## REFERENCE: Type Hint Patterns

### Pattern 1: Optional Return
```python
def find_file(name: str) -> Optional[Path]:
    if exists(name):
        return Path(name)
    return None
```

### Pattern 2: Union Types (Python 3.10+)
```python
def process(value: str | int) -> str:
    return str(value)
```

### Pattern 3: Generic Collections
```python
def get_items() -> List[Dict[str, Any]]:
    return [{"key": "value"}]
```

### Pattern 4: Callable
```python
def apply(func: Callable[[int], str], value: int) -> str:
    return func(value)
```

### Pattern 5: TypeAlias (Complex Types)
```python
MetadataDict = Dict[str, str]
ConflictList = List[Dict[str, Any]]

def parse_metadata(data: str) -> MetadataDict:
    pass
```

---

## WHEN COMPLETE

1. Mark task as complete in `.claude/TASKS.md`
2. Commit changes:
   ```bash
   git add .
   git commit -m "feat: Add comprehensive type hints for mypy --strict compliance"
   ```
3. Update `.claude/state.md` with completion
4. Celebrate! 🎉

---

**Status**: Documented, ready for verification when mypy is installed
**Next Task**: B3 - Integration Tests (proceeding now)
