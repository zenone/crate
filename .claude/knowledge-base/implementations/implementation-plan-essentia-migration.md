# Implementation Plan: Migrate from librosa to Essentia

**Date**: 2026-01-30
**Task**: #88
**Complexity**: HIGH
**Risk Level**: MEDIUM-HIGH
**Estimated Effort**: 4-6 hours implementation + testing

---

## Executive Summary

**Goal**: Replace librosa with Essentia for audio analysis (BPM and key detection)

**Why**:
- ✅ **Accuracy**: Essentia is industry-standard (used by Spotify)
- ✅ **Speed**: C++ based, 2-3x faster than librosa
- ✅ **Quality**: Better algorithms (RhythmExtractor2013, KeyExtractor)
- ⚠️ **Trade-off**: Harder installation (C++ dependencies)

**Recommendation**: Proceed with migration, but implement as **optional fallback** to librosa

---

## BEFORE Phase: Complete Analysis

### 1. User Journey Analysis

```
Current Flow (librosa):
1. User enables "Auto-detect BPM" or "Auto-detect Key"
2. File loaded → No ID3 tag → Triggers audio analysis
3. librosa analyzes audio (60s for BPM, 30s for key)
4. Result displayed in UI
5. User sees source badge: "🤖 AI"

Proposed Flow (Essentia):
1. User enables "Auto-detect BPM" or "Auto-detect Key"
2. File loaded → No ID3 tag → Triggers audio analysis
3. Try Essentia first (if available)
   → If Essentia fails: Fall back to librosa
   → If librosa not available: Show "Unavailable"
4. Result displayed in UI
5. User sees source badge: "🤖 AI" (same)

Then what? User doesn't care which library is used, just wants accuracy
```

### 2. Side Effects Analysis

**Installation**:
- Essentia requires C++ build tools
- May fail on some systems (Windows especially)
- librosa is pure Python (always works)

**Performance**:
- Essentia: 2-3x faster (C++ optimized)
- librosa: Slower but reliable
- Impact: Noticeable on large libraries (1000+ files)

**Accuracy**:
- Essentia BPM: ~95% accuracy (industry standard)
- librosa BPM: ~85% accuracy (good but not best)
- Essentia Key: ~80% accuracy (better algorithms)
- librosa Key: ~60-70% accuracy (simple chromagram)

**Dependencies**:
- Essentia: ~100MB (includes models)
- librosa: ~30MB
- Impact: Larger Docker images, longer install time

**Code Changes**:
- New file: `audio_analysis_essentia.py`
- Modify: `audio_analysis.py` (add fallback logic)
- No changes to API contracts (same function signatures)
- No frontend changes needed

### 3. User Intent

**What users want**:
- Accurate BPM detection
- Accurate key detection
- Fast analysis
- Reliable (doesn't crash)

**What users don't want**:
- Installation failures
- Breaking changes
- Slower performance
- Less accuracy

**Conservative approach**: Make Essentia **optional** with librosa fallback

### 4. Implementation Options

#### Option A: Replace librosa completely (AGGRESSIVE)

**Approach**: Remove librosa, use only Essentia

**Pros**:
- Simpler code (one library only)
- Best accuracy
- Fastest performance
- Forces users to get best experience

**Cons**:
- Installation might fail (especially Windows)
- Breaking change for existing users
- No fallback if Essentia unavailable
- Requires migration guide

**Risk**: HIGH

---

#### Option B: Essentia with librosa fallback (RECOMMENDED)

**Approach**: Try Essentia first, fall back to librosa if unavailable

**Pros**:
- Best of both worlds (accuracy + reliability)
- Non-breaking change
- Works on all systems
- Graceful degradation
- Users can choose (install Essentia or not)

**Cons**:
- More complex code (two implementations)
- Larger dependencies (both libraries)
- Need to maintain both

**Risk**: MEDIUM

---

#### Option C: Essentia only, manual opt-in (CONSERVATIVE)

**Approach**: Keep librosa as default, add setting to enable Essentia

**Pros**:
- No breaking changes
- Users choose when ready
- Can test Essentia before switching
- Safe rollback

**Cons**:
- Most users won't discover Essentia
- Complex settings UI
- Dual code paths forever

**Risk**: LOW

---

### 5. Recommendation

**Choose Option B**: Essentia with librosa fallback

**Reasoning**:
- Best user experience (automatic accuracy improvement)
- Graceful degradation (works everywhere)
- Non-breaking (existing users unaffected)
- Future-proof (can remove librosa later if Essentia adoption high)

**Implementation Strategy**:
1. Add Essentia support (new file)
2. Modify main file to try Essentia → fallback to librosa
3. Log which library was used
4. No UI changes needed
5. Update documentation

---

## Implementation Plan

### Phase 1: Add Essentia Support

**File**: `crate/core/audio_analysis_essentia.py` (NEW)

**Functions to implement**:
```python
def detect_bpm_essentia(file_path: Path, logger) -> Tuple[Optional[str], str]:
    """
    Detect BPM using Essentia's RhythmExtractor2013.
    Returns: (bpm_string, "Analyzed") or (None, "Failed")
    """

def detect_key_essentia(file_path: Path, logger) -> Tuple[Optional[str], str]:
    """
    Detect key using Essentia's KeyExtractor.
    Returns: (key_string, "Analyzed") or (None, "Failed")
    """
```

**Essentia Algorithms**:
- **BPM**: `RhythmExtractor2013` (industry standard)
- **Key**: `KeyExtractor` (Temperley algorithm)

**Error Handling**:
- Try/catch for import errors
- Try/catch for analysis errors
- Return None/"Failed" on error (same as librosa)

---

### Phase 2: Add Fallback Logic

**File**: `crate/core/audio_analysis.py` (MODIFY)

**Current**:
```python
def detect_bpm_from_audio(file_path, logger):
    if not LIBROSA_AVAILABLE:
        return None, "Unavailable"
    # Use librosa
```

**New**:
```python
def detect_bpm_from_audio(file_path, logger):
    # Try Essentia first (if available)
    if ESSENTIA_AVAILABLE:
        try:
            result = detect_bpm_essentia(file_path, logger)
            if result[0] is not None:
                logger.debug(f"Used Essentia for BPM: {result[0]}")
                return result
        except Exception as e:
            logger.warning(f"Essentia failed, falling back to librosa: {e}")

    # Fall back to librosa
    if LIBROSA_AVAILABLE:
        logger.debug("Using librosa for BPM")
        return detect_bpm_librosa(file_path, logger)

    # Neither available
    return None, "Unavailable"
```

**Same pattern for key detection**

---

### Phase 3: Testing

**Test Cases**:

1. **Essentia installed + works**
   - Should use Essentia
   - Log: "Used Essentia"
   - Result: Accurate BPM/key

2. **Essentia installed + fails on specific file**
   - Should fall back to librosa
   - Log: "Essentia failed, falling back"
   - Result: librosa BPM/key

3. **Essentia not installed, librosa available**
   - Should use librosa
   - Log: "Using librosa"
   - Result: librosa BPM/key

4. **Neither installed**
   - Should return "Unavailable"
   - No crashes

5. **Accuracy comparison**
   - Test on 100 tracks with known BPM/key
   - Compare Essentia vs librosa accuracy
   - Document improvement

---

### Phase 4: Documentation

**Update files**:
- `README.md`: Document Essentia as optional dependency
- `requirements.txt`: Add `essentia==2.1b6.dev1110` (optional)
- `docs/installation.md`: Add Essentia installation guide
- `docs/audio-analysis.md`: Document library selection logic

**Installation Guide**:
```bash
# Linux/macOS (recommended)
pip install essentia

# Windows (may require build tools)
# Option 1: Conda
conda install -c mtg essentia

# Option 2: Docker (if native fails)
# Use pre-built Docker image with Essentia
```

---

## Technical Specifications

### Essentia API Usage

**BPM Detection**:
```python
import essentia.standard as es

# Load audio
loader = es.MonoLoader(filename=str(file_path))
audio = loader()

# Extract rhythm
rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
bpm, _, _, _, _ = rhythm_extractor(audio)

# Validate and return
if 60 <= bpm <= 200:
    return str(int(round(bpm))), "Analyzed"
```

**Key Detection**:
```python
import essentia.standard as es

# Load audio
loader = es.MonoLoader(filename=str(file_path))
audio = loader()

# Extract key
key_extractor = es.KeyExtractor()
key, scale, strength = key_extractor(audio)

# Convert scale: "major" → "maj", "minor" → "min"
scale_short = "maj" if scale == "major" else "min"
return f"{key} {scale_short}", "Analyzed"
```

---

## Migration Checklist

### Pre-Implementation
- [x] Read current audio_analysis.py implementation
- [x] Research Essentia capabilities
- [x] Document trade-offs
- [x] Choose implementation strategy (Option B)
- [x] Create test plan

### Implementation
- [ ] Create `audio_analysis_essentia.py`
- [ ] Implement `detect_bpm_essentia()`
- [ ] Implement `detect_key_essentia()`
- [ ] Add availability check (`ESSENTIA_AVAILABLE`)
- [ ] Modify `audio_analysis.py` fallback logic
- [ ] Refactor librosa code to `detect_bpm_librosa()`
- [ ] Add comprehensive logging
- [ ] Test import both/either/neither scenarios

### Testing
- [ ] Test with Essentia installed (happy path)
- [ ] Test with only librosa (fallback path)
- [ ] Test with neither (unavailable path)
- [ ] Test Essentia failure → librosa fallback
- [ ] Accuracy test on sample tracks
- [ ] Performance benchmark (speed comparison)
- [ ] Windows compatibility test (if possible)

### Documentation
- [ ] Update README.md
- [ ] Update requirements.txt (essentia optional)
- [ ] Create installation guide
- [ ] Document library selection logic
- [ ] Add troubleshooting guide

### Deployment
- [ ] Feature flag ready (can disable Essentia if issues)
- [ ] Rollback plan documented
- [ ] User notification (changelog)

---

## Risk Assessment

### HIGH Risk Items

**1. Installation Failures**
- **Risk**: Essentia fails to install on Windows
- **Mitigation**: Fallback to librosa (automatic)
- **Impact**: Low (users get librosa, same as before)

**2. Performance Regression**
- **Risk**: Essentia slower than expected on some systems
- **Mitigation**: Can disable via feature flag
- **Impact**: Medium (but unlikely - Essentia is faster)

### MEDIUM Risk Items

**3. API Differences**
- **Risk**: Essentia returns different format than expected
- **Mitigation**: Comprehensive testing before release
- **Impact**: Low (isolated to analysis module)

**4. Dependency Bloat**
- **Risk**: Essentia + librosa = large install
- **Mitigation**: Make essentia truly optional
- **Impact**: Low (users can choose)

### LOW Risk Items

**5. Accuracy Differences**
- **Risk**: Essentia accuracy not as advertised
- **Mitigation**: Run accuracy benchmark before release
- **Impact**: Low (can revert to librosa-only)

---

## Success Criteria

**Must Have**:
- ✅ Essentia detection works when installed
- ✅ Graceful fallback to librosa
- ✅ No crashes when neither installed
- ✅ No breaking changes to API
- ✅ Installation guide complete

**Should Have**:
- ✅ BPM accuracy improved by 5%+
- ✅ Key accuracy improved by 10%+
- ✅ Performance 2x faster
- ✅ Works on macOS + Linux

**Nice to Have**:
- ○ Works on Windows
- ○ 90%+ accuracy on test set
- ○ User-visible quality improvement

---

## Rollback Plan

**If issues arise**:

1. **Immediate** (< 1 hour):
   - Set `ESSENTIA_AVAILABLE = False` at top of file
   - Falls back to librosa automatically
   - No code changes needed

2. **Short-term** (< 1 day):
   - Remove essentia import
   - Remove `audio_analysis_essentia.py`
   - Revert to librosa-only

3. **Long-term** (if needed):
   - Document why Essentia didn't work
   - Research alternatives
   - Keep librosa as standard

---

## Performance Benchmarks (Expected)

| Metric | librosa | Essentia | Improvement |
|--------|---------|----------|-------------|
| **BPM Detection Time** | 3-5s | 1-2s | 50-60% faster |
| **Key Detection Time** | 2-3s | 1-1.5s | 40-50% faster |
| **BPM Accuracy** | 85% | 95% | +10% |
| **Key Accuracy** | 65% | 80% | +15% |
| **Install Size** | 30MB | 100MB | +70MB |

*Benchmarks to be verified during testing*

---

## Timeline

**Estimated**: 4-6 hours total

- **Phase 1** (Implementation): 2-3 hours
  - Create essentia module: 1 hour
  - Add fallback logic: 1 hour
  - Error handling: 30 min

- **Phase 2** (Testing): 1-2 hours
  - Unit tests: 30 min
  - Integration tests: 30 min
  - Accuracy benchmark: 1 hour

- **Phase 3** (Documentation): 1 hour
  - README update: 15 min
  - Installation guide: 30 min
  - Troubleshooting: 15 min

---

## Next Steps

**If Approved**:

1. Install Essentia for testing:
   ```bash
   pip install essentia
   ```

2. Create `audio_analysis_essentia.py`

3. Implement BPM and key detection

4. Add fallback logic

5. Test all scenarios

6. Update documentation

7. Request user testing

**Questions for User**:
1. Do you have Essentia installed, or should I include installation as part of implementation?
2. Do you have test tracks with known BPM/key for accuracy benchmarking?
3. Are you primarily on macOS/Linux or do you need Windows support?

---

## References

- **Essentia Documentation**: https://essentia.upf.edu/
- **RhythmExtractor2013**: https://essentia.upf.edu/reference/std_RhythmExtractor2013.html
- **KeyExtractor**: https://essentia.upf.edu/reference/std_KeyExtractor.html
- **librosa Documentation**: https://librosa.org/

---

## Tags

`#task-88` `#essentia` `#librosa` `#audio-analysis` `#migration` `#implementation-plan` `#high-risk` `#optional-dependency`
