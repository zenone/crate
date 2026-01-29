# TASK B2: Complete Type Hints for mypy --strict

**Date**: 2026-01-28
**Priority**: MEDIUM
**Estimated**: 2 hours
**TWO-PHASE**: This is the improved prompt (Phase 1)

---

## IMPROVED PROMPT - B2: Complete Type Hints

**Role**: Senior Python Developer + Type Safety Expert

**Objective**: Add comprehensive type hints to all modules to achieve 100% mypy --strict compliance. Improve code maintainability, IDE auto-complete, and catch bugs at type-check time.

**Scope**:
- **Files to Modify**: All Python modules in `dj_mp3_renamer/` missing type hints
- **Focus Areas**:
  - `core/audio_analysis.py` - Most critical (missing many hints)
  - `api/renamer.py` - Some hints missing
  - `tui/app.py` - Optional (UI layer, lower priority)
  - All other modules - Verify completeness
- **Out of Scope**: External dependencies, test files (can be typed later)

**Current State**:
```bash
$ mypy dj_mp3_renamer/ --strict
# Expected: Many errors about missing type hints
```

**Implementation Requirements**:

### 1. Add Missing Type Hints
- **Function signatures**: All parameters and return types
- **Variable annotations**: Where type inference unclear
- **Generic types**: List[str], Dict[str, Any], Optional[Path]
- **Union types**: Use `|` operator (Python 3.10+) or Union[]
- **Type aliases**: For complex types used multiple times

### 2. Handle Special Cases
- **Optional types**: Use Optional[T] or T | None
- **Any types**: Minimize use, document why when necessary
- **Callable types**: Specify parameter and return types
- **Protocol types**: For duck typing (if needed)
- **Literal types**: For string constants
- **TypedDict**: For structured dictionaries

### 3. Module-by-Module Approach

#### **core/audio_analysis.py** (Highest Priority)
```python
# Current (missing hints)
def detect_bpm_from_audio(file_path, logger):
    ...

# Target
def detect_bpm_from_audio(file_path: Path, logger: logging.Logger) -> Tuple[Optional[str], str]:
    """
    Detect BPM from audio file using librosa.

    Returns:
        Tuple of (bpm_string, source)
        - bpm_string: BPM as string or None if failed
        - source: "Analyzed" | "Failed" | "Unavailable"
    """
    ...
```

**Functions to type:**
- `detect_bpm_from_audio()` - lines 31-92
- `detect_key_from_audio()` - lines 95-172
- `auto_detect_metadata()` - lines 173-252
- `lookup_acoustid()` - lines 255-323
- Helper functions if any

#### **api/renamer.py** (Medium Priority)
- Verify `RenamerAPI.__init__()` types
- Check `_rename_one()` return type
- Check `_enhance_metadata()` return type
- Check `_derive_target()` return type

#### **Other Modules** (Lower Priority)
- Scan all modules for missing hints
- Add hints where needed
- Prioritize public APIs over internal helpers

### 4. Type Checking Strategy
```python
# Use TYPE_CHECKING for circular imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dj_mp3_renamer.core.io import ReservationBook
```

### 5. Special Python Features
- **Overload**: For functions with multiple signatures
- **Generic**: For reusable generic functions
- **ParamSpec**: For decorators preserving signatures
- **TypeVar**: For generic type variables

**Test Requirements**:
1. Run: `mypy dj_mp3_renamer/ --strict` - Should pass with 0 errors
2. Run: `mypy dj_mp3_renamer/ --strict --show-error-codes` - Check error types
3. Run existing tests: `pytest tests/ -v` - All 162 tests must still pass
4. Check IDE: Open files in VS Code/PyCharm - Verify auto-complete works

**Definition of Done**:
- [ ] All functions have parameter and return type hints
- [ ] All class methods have type hints
- [ ] Complex types documented with TypeAlias
- [ ] `mypy dj_mp3_renamer/ --strict` passes with 0 errors
- [ ] All 162 existing tests still pass
- [ ] No use of `Any` except where documented as necessary
- [ ] Type hints improve IDE auto-complete (verified manually)
- [ ] Changes committed with message: `feat: Add comprehensive type hints for mypy --strict compliance`

**Verification Commands**:
```bash
# Type check with strict mode
mypy dj_mp3_renamer/ --strict

# Show error codes for debugging
mypy dj_mp3_renamer/ --strict --show-error-codes

# Check specific modules
mypy dj_mp3_renamer/core/audio_analysis.py --strict

# Run tests
pytest tests/ -v

# Check coverage unchanged
pytest tests/ --cov=dj_mp3_renamer --cov-report=term
```

**Acceptance Criteria**:
1. ✅ mypy --strict passes (0 errors)
2. ✅ All existing tests pass (162/162)
3. ✅ IDE auto-complete improved
4. ✅ Type hints are accurate (not just Any everywhere)
5. ✅ Documentation updated (if needed)

**Constraints**:
1. **No Breaking Changes**: Existing function signatures unchanged
2. **No Behavior Changes**: Only add type annotations
3. **Python 3.8+ Compatible**: Use types available in 3.8+
4. **Minimal Use of Any**: Document why when used
5. **Follow PEP 484**: Type hinting best practices

**Best Practices (2025-2026)**:
- Use `list[str]` not `List[str]` (Python 3.9+ lowercase generics)
- Use `str | None` not `Optional[str]` (Python 3.10+ union syntax)
- Use `TypeAlias` for complex types
- Document generic constraints with TypeVar bounds
- Use Protocol for structural subtyping
- Add py.typed marker for library type support

---

## ASSUMPTIONS:
1. Python 3.8+ is the minimum version (current setup)
2. mypy is already installed (check requirements-dev.txt)
3. Type hints should not change runtime behavior
4. Some functions may legitimately need `Any` (document why)
5. librosa/acoustid types may be incomplete (use TYPE_CHECKING imports)

---

## PHASE 2: EXECUTION READY

This improved prompt is ready for execution. Proceed with implementation.
