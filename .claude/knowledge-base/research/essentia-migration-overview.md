# Essentia Migration - High-Level Overview

**Date**: 2026-01-30
**Priority**: HIGH (after critical bugs fixed)
**Estimated Effort**: Medium (1-2 weeks)
**Status**: Planning Phase

---

## Executive Summary

Migrate audio analysis from **librosa** to **Essentia** for 2-3x performance improvement and better accuracy for DJ/electronic music.

### Why Essentia?

| Feature | librosa | Essentia | Winner |
|---------|---------|----------|--------|
| **Performance** | Baseline | 2-3x faster | ✅ Essentia |
| **BPM Accuracy (EDM)** | Good | Excellent | ✅ Essentia |
| **Key Detection** | Good | Better | ✅ Essentia |
| **Industry Use** | General purpose | DJ software (Mixxx) | ✅ Essentia |
| **Algorithms** | ~50 | 200+ | ✅ Essentia |
| **Installation** | pip install | pip install | 🟰 Tie |
| **Python API** | Simple | More complex | ⚠️ librosa |
| **Learning Curve** | Low | Medium | ⚠️ librosa |

**Bottom Line**: Essentia is faster and more accurate for our DJ use case, but requires more effort to integrate.

---

## Current Implementation (librosa)

### Where We Use librosa

**File**: `/Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename/crate/core/audio_analysis.py`

**Functions**:
1. **BPM Detection**: `librosa.beat.beat_track()`
2. **Key Detection**: `librosa.feature.chroma_cqt()` + custom key estimation

**Code Pattern**:
```python
import librosa

def analyze_bpm(file_path: str) -> Optional[int]:
    y, sr = librosa.load(file_path, duration=60)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    return round(tempo)

def analyze_key(file_path: str) -> Optional[str]:
    y, sr = librosa.load(file_path, duration=60)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    # ... key estimation logic ...
```

---

## Proposed Implementation (Essentia)

### Installation

```bash
pip install essentia
```

**Note**: Essentia has pre-built wheels for macOS, Linux, Windows. No compilation needed.

### API Differences

#### BPM Detection
```python
# OLD (librosa)
y, sr = librosa.load(file_path)
tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

# NEW (Essentia)
import essentia.standard as es

audio = es.MonoLoader(filename=file_path, sampleRate=44100)()
rhythm_extractor = es.RhythmExtractor2013()
bpm, beats, beats_confidence, _, _ = rhythm_extractor(audio)
```

**Key Differences**:
- Essentia uses `MonoLoader` instead of `librosa.load()`
- RhythmExtractor2013 returns more detailed beat information
- BPM confidence score available (can filter low-confidence results)

#### Key Detection
```python
# OLD (librosa)
chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
# Custom key estimation

# NEW (Essentia)
key_extractor = es.KeyExtractor()
key, scale, strength = key_extractor(audio)
```

**Key Differences**:
- Essentia has built-in key extractor (no custom logic needed)
- Returns key (C, D, E...), scale (major/minor), and confidence strength
- More accurate for electronic music

---

## Migration Strategy

### Phase 1: Research & Prototyping (3 days)
1. Install Essentia in development environment
2. Create prototype script to test BPM/key detection accuracy
3. Compare results with librosa on test album (Alabama Shakes, electronic music)
4. Document API differences and gotchas

### Phase 2: Compatibility Layer (2 days)
1. Create abstraction layer in `audio_analysis.py`
2. Add config option: `audio_engine: "librosa" | "essentia"`
3. Implement both backends behind same interface
4. Allow A/B testing

**Example**:
```python
class AudioAnalyzer:
    def __init__(self, engine: str = "librosa"):
        self.engine = engine

    def analyze_bpm(self, file_path: str) -> Optional[int]:
        if self.engine == "librosa":
            return self._analyze_bpm_librosa(file_path)
        elif self.engine == "essentia":
            return self._analyze_bpm_essentia(file_path)
```

### Phase 3: Essentia Implementation (3 days)
1. Implement `_analyze_bpm_essentia()`
2. Implement `_analyze_key_essentia()`
3. Add error handling and fallbacks
4. Add confidence thresholds

### Phase 4: Testing & Validation (2 days)
1. Unit tests for both engines
2. Performance benchmarking
3. Accuracy comparison on DJ's music collection
4. Edge case testing (corrupted files, short files, etc.)

### Phase 5: Migration & Cleanup (2 days)
1. Update config default to "essentia"
2. Update documentation
3. Deprecate librosa (keep for fallback)
4. Performance monitoring in production

**Total Estimated Time**: 10-12 days

---

## Technical Considerations

### Dependencies

**Current** (`requirements.txt`):
```
librosa==0.10.1
```

**After Migration**:
```
librosa==0.10.1  # Keep for fallback
essentia==2.1b6.dev1110  # Add new
```

**Size Impact**:
- librosa: ~50 MB
- Essentia: ~20 MB (C++ optimized)
- **Net**: May actually reduce footprint

### Performance Impact

**Expected Improvements**:
- BPM detection: 2-3x faster
- Key detection: 2-3x faster
- Memory usage: ~30% lower (C++ core)

**Example Benchmark** (100 files):
- librosa: ~5 minutes
- Essentia: ~2 minutes
- **Savings**: 60% faster

### Breaking Changes

**None expected** - Compatibility layer ensures transparent migration.

**User-facing changes**:
- (Optional) New config option: `audio_engine`
- Potentially more accurate BPM/key values
- Faster metadata loading

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Essentia install fails on some platforms | HIGH | Keep librosa as fallback, auto-detect |
| Different BPM/key results confuse users | MEDIUM | Document differences, add A/B comparison tool |
| API differences cause bugs | MEDIUM | Comprehensive testing, gradual rollout |
| Learning curve for maintenance | LOW | Good documentation, simple abstraction |

---

## Success Metrics

### Performance
- [ ] BPM detection ≥2x faster
- [ ] Key detection ≥2x faster
- [ ] Memory usage ≤ current baseline

### Accuracy
- [ ] BPM accuracy on electronic music ≥ librosa
- [ ] Key accuracy on DJ collection ≥ librosa
- [ ] User-reported accuracy improvements

### Reliability
- [ ] 0 regressions in existing tests
- [ ] Essentia engine passes all unit tests
- [ ] Fallback to librosa works automatically

---

## Resources

### Official Documentation
- [Essentia Documentation](https://essentia.upf.edu/documentation.html)
- [Essentia Python Tutorial](https://essentia.upf.edu/python_tutorial.html)
- [Essentia Algorithms Reference](https://essentia.upf.edu/algorithms_reference.html)

### Relevant Examples
- [RhythmExtractor2013](https://essentia.upf.edu/reference/std_RhythmExtractor2013.html)
- [KeyExtractor](https://essentia.upf.edu/reference/std_KeyExtractor.html)
- [Mixxx Integration](https://github.com/mixxxdj/mixxx) - Real-world example

### Research Papers
- Zapata et al. (2013): Multi-feature beat tracking
- Gomez (2006): Chroma features and key estimation

---

## Next Steps

1. **Immediate**: Create GitHub issue for tracking
2. **Week 1**: Install Essentia, run prototype tests
3. **Week 2**: Implement compatibility layer
4. **Week 3**: Full implementation and testing
5. **Week 4**: Documentation and rollout

---

## Questions for User

Before starting implementation:

1. **Priority**: Should we do this before or after "Remember last directory" feature?
2. **Testing**: Do you have a specific album/collection you want us to test BPM/key accuracy on?
3. **Rollout**: Gradual (config option) or immediate (replace librosa)?
4. **Performance**: What's your typical batch size? (helps prioritize performance work)

---

**Status**: Awaiting user feedback and priority confirmation
**Tracked**: Task #88 in task list
