# TASK B4: Implement Config Caching

**Date**: 2026-01-28
**Priority**: MEDIUM
**Estimated**: 2 hours
**TWO-PHASE**: This is the improved prompt (Phase 1)

---

## IMPROVED PROMPT - B4: Config Caching

**Role**: Senior Performance Engineer + Python Optimization Expert

**Objective**: Add intelligent config file caching to eliminate redundant file reads during batch operations. Currently, the config file is read on every access, causing unnecessary I/O overhead when processing hundreds or thousands of MP3 files.

**Performance Impact**:
- **Current**: Read config file N times for N operations
- **Target**: Read config file once, cache with mtime validation
- **Expected Speedup**: 10-50ms saved per file operation (significant for 1000+ files)

---

## PROBLEM ANALYSIS

### Current Behavior
```python
# core/config.py (current)
def load_config() -> dict:
    """Load config from config.yaml - NO CACHING"""
    config_file = Path.home() / ".dj_mp3_renamer" / "config.yaml"
    if not config_file.exists():
        return {}

    with open(config_file) as f:
        return yaml.safe_load(f)  # Read file every time!

# This gets called repeatedly during batch operations
```

**Problem**: When renaming 1000 files, this function is called 1000+ times, reading the same config file 1000+ times.

### Root Cause
- No caching mechanism
- No mtime (modification time) checking
- No cache invalidation strategy

---

## SOLUTION DESIGN

### Caching Strategy
Use a module-level cache with mtime-based invalidation:

```python
# core/config.py (improved)

from pathlib import Path
from typing import Tuple, Optional
import yaml

# Module-level cache
_config_cache: Optional[dict] = None
_config_mtime: Optional[float] = None

def load_config() -> dict:
    """
    Load config from config.yaml with intelligent caching.

    Caching Strategy:
    - Cache config in memory after first read
    - Track file modification time (mtime)
    - Invalidate cache if file modified
    - Return cached config if file unchanged

    Returns:
        Config dictionary (empty dict if file missing)
    """
    global _config_cache, _config_mtime

    config_file = Path.home() / ".dj_mp3_renamer" / "config.yaml"

    # If file doesn't exist, return empty dict (no caching needed)
    if not config_file.exists():
        return {}

    # Get current file modification time
    current_mtime = config_file.stat().st_mtime

    # Cache hit: File unchanged since last read
    if _config_cache is not None and _config_mtime == current_mtime:
        return _config_cache.copy()  # Return copy to prevent mutation

    # Cache miss: Read file and update cache
    with open(config_file) as f:
        config = yaml.safe_load(f) or {}

    _config_cache = config
    _config_mtime = current_mtime

    return config.copy()  # Return copy to prevent mutation


def clear_config_cache() -> None:
    """
    Clear the config cache.

    Useful for:
    - Testing (reset between tests)
    - Force reload after programmatic config changes
    - Memory management (though cache is tiny)
    """
    global _config_cache, _config_mtime
    _config_cache = None
    _config_mtime = None
```

---

## IMPLEMENTATION REQUIREMENTS

### 1. Add Caching to `core/config.py`

**Files to Modify**: `dj_mp3_renamer/core/config.py`

**Changes**:
- Add module-level cache variables (`_config_cache`, `_config_mtime`)
- Modify `load_config()` to implement caching logic
- Add `clear_config_cache()` helper function
- Add docstrings explaining caching behavior

**Important**:
- Return `.copy()` of cached dict to prevent mutation
- Use `st_mtime` for modification time detection
- Handle edge cases (missing file, permission errors)

---

### 2. Add Tests to `tests/test_config.py`

**Files to Modify**: `tests/test_config.py`

**Tests to Add**:

#### Test 1: Cache Hit (Same File Content)
```python
def test_config_caching_hit(tmp_path):
    """
    Test: Config is cached when file unchanged.

    Scenario:
    1. Create config file
    2. Load config (cache miss, reads file)
    3. Load config again (cache hit, no read)
    4. Verify both loads return same data
    5. Verify file only read once
    """
    config_file = tmp_path / "config.yaml"
    config_file.write_text("default_template: '{artist} - {title}'")

    # Mock file read to count calls
    original_open = open
    read_count = 0

    def counting_open(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        return original_open(*args, **kwargs)

    with patch("builtins.open", counting_open):
        config1 = load_config()
        config2 = load_config()

    assert config1 == config2
    assert read_count == 1  # File read only once
```

#### Test 2: Cache Miss (File Modified)
```python
def test_config_caching_invalidation(tmp_path):
    """
    Test: Cache invalidates when file modified.

    Scenario:
    1. Create config file with value A
    2. Load config (cache miss, reads file)
    3. Modify config file with value B
    4. Load config again (cache miss, reads file again)
    5. Verify second load returns value B
    """
    config_file = tmp_path / "config.yaml"
    config_file.write_text("template: 'A'")

    config1 = load_config()
    assert config1["template"] == "A"

    # Modify file (change mtime)
    time.sleep(0.01)  # Ensure mtime changes
    config_file.write_text("template: 'B'")

    config2 = load_config()
    assert config2["template"] == "B"
    assert config1 != config2  # Different values
```

#### Test 3: Cache Isolation (No Mutation)
```python
def test_config_cache_isolation(tmp_path):
    """
    Test: Cached config is isolated from mutations.

    Scenario:
    1. Load config
    2. Mutate returned dict
    3. Load config again
    4. Verify mutation didn't affect cache
    """
    config_file = tmp_path / "config.yaml"
    config_file.write_text("key: 'original'")

    config1 = load_config()
    config1["key"] = "mutated"  # Mutate returned dict

    config2 = load_config()
    assert config2["key"] == "original"  # Cache unaffected
```

#### Test 4: Cache Clear
```python
def test_config_cache_clear():
    """
    Test: clear_config_cache() resets cache.

    Scenario:
    1. Load config (cache populated)
    2. Clear cache
    3. Load config again (cache miss)
    """
    config_file = tmp_path / "config.yaml"
    config_file.write_text("key: 'value'")

    load_config()  # Populate cache

    # Clear cache
    clear_config_cache()

    # Next load should read file again (cache miss)
    # (Verify by mocking or checking internal state)
```

#### Test 5: Missing File Handling
```python
def test_config_caching_missing_file():
    """
    Test: Missing config file handled gracefully.

    Scenario:
    1. Load config when file doesn't exist
    2. Verify returns empty dict
    3. Verify no caching of non-existent file
    """
    # Ensure config file doesn't exist
    config_file = Path("/nonexistent/config.yaml")

    config = load_config()
    assert config == {}

    # Should not crash on repeated calls
    config2 = load_config()
    assert config2 == {}
```

---

### 3. Benchmark Performance Impact

Create a simple benchmark script to verify improvement:

```python
# scripts/benchmark_config.py

import time
from pathlib import Path
from dj_mp3_renamer.core.config import load_config, clear_config_cache

def benchmark_without_cache(iterations=1000):
    """Benchmark config loading without cache (simulate old behavior)."""
    start = time.time()
    for _ in range(iterations):
        clear_config_cache()  # Force cache miss
        load_config()
    elapsed = time.time() - start
    return elapsed

def benchmark_with_cache(iterations=1000):
    """Benchmark config loading with cache."""
    clear_config_cache()  # Start fresh
    start = time.time()
    for _ in range(iterations):
        load_config()  # Should hit cache after first load
    elapsed = time.time() - start
    return elapsed

if __name__ == "__main__":
    print("Benchmarking config caching...")
    print(f"Without cache (1000 loads): {benchmark_without_cache():.3f}s")
    print(f"With cache (1000 loads): {benchmark_with_cache():.3f}s")
    print("Speedup: {:.1f}x".format(
        benchmark_without_cache() / benchmark_with_cache()
    ))
```

**Expected Results**:
- Without cache: ~50-100ms (1000 file reads)
- With cache: ~5-10ms (1 file read + 999 cache hits)
- Speedup: 10-20x for repeated loads

---

## EDGE CASES TO HANDLE

### 1. **Concurrent Access**
- Current implementation: Module-level cache is thread-safe for reads (GIL protection)
- No write conflicts (config rarely changes during processing)
- If needed, add threading.Lock for complete safety

### 2. **Config File Permissions**
```python
try:
    current_mtime = config_file.stat().st_mtime
except (OSError, PermissionError):
    # File exists but can't read stats
    return {}
```

### 3. **YAML Parse Errors**
```python
try:
    with open(config_file) as f:
        config = yaml.safe_load(f) or {}
except yaml.YAMLError:
    # Invalid YAML, return empty config
    return {}
```

### 4. **Race Conditions (File Modified During Read)**
- Low risk: Config file is small, reads are atomic
- mtime check happens before read, not after
- Acceptable edge case (next load will get new version)

---

## TESTING STRATEGY

### Unit Tests (Required)
- Test cache hit (repeated loads)
- Test cache invalidation (file modified)
- Test cache isolation (no mutation)
- Test cache clear
- Test missing file
- Test permission errors
- Test invalid YAML

### Integration Tests (Optional)
- Test caching during full rename operation
- Verify config read only once per batch
- Verify config changes detected mid-batch (if applicable)

### Performance Tests (Optional but Recommended)
- Benchmark script (scripts/benchmark_config.py)
- Compare before/after performance
- Document speedup in commit message

---

## ACCEPTANCE CRITERIA

- [ ] `load_config()` implements mtime-based caching
- [ ] `clear_config_cache()` helper function added
- [ ] Module-level cache variables added (`_config_cache`, `_config_mtime`)
- [ ] Cached dict is copied to prevent mutation
- [ ] 5+ tests added to `tests/test_config.py`
- [ ] All existing tests still pass (162 + 8 + new tests)
- [ ] Benchmark shows 10x+ speedup for repeated loads
- [ ] Edge cases handled (missing file, permissions, parse errors)
- [ ] Docstrings explain caching behavior
- [ ] Changes committed with message: `perf: Add mtime-based config caching for batch operations`

---

## VERIFICATION COMMANDS

```bash
# Run config tests
pytest tests/test_config.py -v

# Run all tests
pytest tests/ -v

# Benchmark performance (if script created)
python scripts/benchmark_config.py

# Check test coverage
pytest tests/test_config.py --cov=dj_mp3_renamer.core.config --cov-report=term
```

---

## EXPECTED OUTCOMES

### Before Caching
```python
# Processing 1000 files
for file in files:  # 1000 iterations
    config = load_config()  # Reads config.yaml 1000 times
    # ... rename logic
```

### After Caching
```python
# Processing 1000 files
for file in files:  # 1000 iterations
    config = load_config()  # Reads config.yaml once, cache hits 999 times
    # ... rename logic
```

**Performance Gain**:
- **Small batches (10 files)**: ~50ms saved
- **Medium batches (100 files)**: ~500ms saved
- **Large batches (1000 files)**: ~5s saved
- **Memory cost**: Negligible (~1KB cache)

---

## CONSTRAINTS

1. **No Breaking Changes**: Existing code continues to work unchanged
2. **Thread Safety**: Cache must be safe for concurrent access (GIL provides read safety)
3. **Memory Efficient**: Cache is tiny (~1KB), no memory concerns
4. **Backward Compatible**: No API changes, drop-in replacement
5. **Edge Case Safe**: Handle missing files, permissions, parse errors gracefully

---

## BEST PRACTICES (2025-2026)

- **Module-level caching**: Simple, effective for read-heavy workloads
- **mtime-based invalidation**: Standard approach for file caching
- **Defensive copying**: Return `.copy()` to prevent cache corruption
- **Clear naming**: `_config_cache` (leading underscore = private)
- **Explicit cache control**: Provide `clear_config_cache()` for testing
- **Type hints**: Annotate cache variables with `Optional[dict]`

---

## ASSUMPTIONS

1. Config file is small (<10KB typically)
2. Config changes are rare during processing
3. File system mtime is reliable (standard assumption)
4. GIL provides sufficient thread safety for reads
5. Python 3.8+ (f.stat().st_mtime available)

---

## PHASE 2: EXECUTION READY

This improved prompt is ready for execution. Proceed with implementation.
