# Task 53-57: Smart Track Number Detection - Design & Implementation Plan

**Date**: 2026-01-30
**Feature**: Intelligent track number context detection
**Approach**: API First, TDD, User Control Preserved

---

## 1. Research Findings

### 1.1 Music Library Best Practices

**Industry Tools**:
- **[Beets](https://beets.io/)**: Music organizer that uses MusicBrainz database for metadata
- **[MusicBrainz](https://musicbrainz.org/)**: Open music encyclopedia with standardized metadata
- **Common Heuristics**: Album detection via shared album tag, sequential track numbers, file grouping

**Key Insight**: Automated heuristics must handle ambiguous cases (language differences, non-standardized spellings, errors) gracefully without forcing incorrect classifications.

**Source**: [Springer - Music Library Metadata Alignment](https://link.springer.com/article/10.1007/s00799-017-0223-9)

### 1.2 Smart Suggestions UI/UX Patterns (2024-2026)

**Co-pilot Pattern**:
- AI acts as collaborative assistant, not autonomous decision-maker
- User retains authorship and final decision-making
- Contextual inline assistance for easy accept/reject/modify
- **Example**: GitHub Copilot suggests code inline, developers can reject/modify/undo

**Automation Controls**:
- Toggles, sliders, or rule-based settings for user control
- Manual override and undo options always available
- **Example**: Gmail Smart Compose can be disabled by user

**Levels of Automation**:
- **No Automation** (Recommended): System provides suggestions, user makes all decisions
- **Example**: Grammarly highlights issues, user accepts/rejects each correction

**Sources**:
- [GenAI UX Patterns](https://uxdesign.cc/20-genai-ux-patterns-examples-and-implementation-tactics-5b1868b7d4a1)
- [Smart Interface Design Patterns](https://smart-interface-design-patterns.com/)

### 1.3 Design Principles Applied

1. **User Control**: Smart mode is opt-in (off by default)
2. **Transparency**: Show detection logic, don't hide decisions
3. **Reversibility**: Users can always override or disable
4. **Contextual**: Suggestions appear inline, non-blocking
5. **Graceful Degradation**: Works with incomplete metadata

---

## 2. Feature Design

### 2.1 Detection Heuristics

#### Algorithm: Album vs Singles Classification

```
FOR each loaded directory:
  files = get_all_files()

  # Group by album tag
  albums = group_by(files, 'album')

  FOR each album_group IN albums:
    IF album_group.album_tag IS empty:
      CLASSIFY as "SINGLES" (no album context)
      CONTINUE

    IF album_group.file_count < 3:
      CLASSIFY as "SINGLES" (too few for album)
      CONTINUE

    # Check track number completeness
    track_numbers = extract_track_numbers(album_group.files)

    IF track_numbers.missing_count > 30% OF total:
      CLASSIFY as "INCOMPLETE_ALBUM" (suggest album format with caution)
      CONTINUE

    IF track_numbers.are_sequential(start=1):
      CLASSIFY as "ALBUM" (high confidence)
      SUGGEST template with {track}
    ELSE:
      CLASSIFY as "PARTIAL_ALBUM" (medium confidence)
      SUGGEST template with {track}, show warning
END
```

#### Classification Criteria

| Classification | Criteria | Confidence | Suggested Template |
|----------------|----------|------------|-------------------|
| **ALBUM** | Same album tag + 3+ files + sequential tracks (1,2,3...) | High (90%+) | `{track} - {artist} - {title}` |
| **PARTIAL_ALBUM** | Same album tag + 3+ files + gaps in tracks | Medium (70%) | `{track} - {artist} - {title}` + warning |
| **INCOMPLETE_ALBUM** | Same album tag + 3+ files + 30%+ missing tracks | Low (50%) | Suggest both formats |
| **SINGLES** | No album tag OR mixed albums OR < 3 files | N/A | `{artist} - {title} [{bpm}]` |

#### Edge Cases Handled

1. **Track Format "1/12"**: Extract "1", check if sequential
2. **Non-numeric tracks**: Ignore, classify as singles
3. **Multiple albums in directory**: Detect each separately, suggest per-group
4. **Zero-padded vs raw**: Normalize (01 = 1) for comparison
5. **Duplicate tracks**: Flag as warning, suggest manual review

### 2.2 API Design

#### New Endpoint: `/api/analyze-context`

**Request**:
```json
POST /api/analyze-context
{
  "files": [
    {
      "path": "/path/to/file1.mp3",
      "metadata": {
        "album": "Album Name",
        "track": "1",
        "artist": "Artist Name",
        "title": "Song Title"
      }
    }
  ]
}
```

**Response**:
```json
{
  "contexts": [
    {
      "type": "ALBUM",
      "confidence": 0.95,
      "album_name": "Album Name",
      "file_count": 12,
      "track_range": "1-12",
      "suggested_templates": [
        {
          "template": "{track} - {artist} - {title}",
          "reason": "Sequential album tracks detected",
          "preset_id": "simple-album"
        },
        {
          "template": "{artist} - {album} - {track} - {title}",
          "reason": "Full album context",
          "preset_id": "full-album"
        }
      ],
      "warnings": []
    }
  ],
  "has_multiple_contexts": false,
  "default_suggestion": {
    "template": "{track} - {artist} - {title}",
    "preset_id": "simple-album"
  }
}
```

**Error Cases**:
- No files: Return empty contexts
- No metadata: Return "SINGLES" classification
- Processing timeout (> 100ms): Return partial results with flag

#### Updated Endpoint: `/api/load-directory`

**Enhancement**: Include context analysis in response (if smart mode enabled)

```json
{
  "files": [...],
  "context_analysis": {
    "enabled": true,
    "contexts": [...]
  }
}
```

### 2.3 UI/UX Design

#### Smart Suggestion Banner (Non-Blocking)

**Location**: Between file list and template preset dropdown

**Visual Design**:
```
┌─────────────────────────────────────────────────────────────┐
│ 💡 Smart Suggestion                                    [×]  │
│                                                              │
│ Detected: Album "Random Access Memories" (13 tracks)        │
│                                                              │
│ Recommended:  [01 - Artist - Title]     [Use This] [Ignore] │
│                                                              │
│ Other options: ▼                                             │
│   • Artist - Album - 01 - Title                              │
│   • Album - 01 - Artist - Title                              │
│   • Enter custom template...                                 │
└─────────────────────────────────────────────────────────────┘
```

**Interactions**:
1. **[Use This]**: Applies suggested template, closes banner
2. **[Ignore]**: Closes banner, user selects template manually
3. **[×]**: Dismisses suggestion, don't show again this session
4. **Other options ▼**: Expands to show 2-3 alternative templates
5. **Enter custom...**: Opens template input with suggestion pre-filled

**States**:
- **High Confidence (>80%)**: Green accent, "Recommended" label
- **Medium Confidence (50-80%)**: Yellow accent, "Suggested" label
- **Low Confidence (<50%)**: Gray accent, "Consider" label + warning icon

#### Settings Integration

**New Setting**: "Smart Track Detection"

```html
<div class="form-group">
    <label class="checkbox-label">
        <input type="checkbox" id="enable-smart-detection" name="enable_smart_detection">
        <span>Enable Smart Track Detection (Beta)</span>
    </label>
    <small class="form-help">
        Automatically suggests album vs single track templates based on metadata.
        You can always override suggestions. Off by default.
    </small>
</div>
```

**Location**: Settings > Other Options section

### 2.4 Configuration Schema

**New Config Options**:
```python
DEFAULT_CONFIG = {
    # ... existing config ...
    "enable_smart_detection": False,  # Off by default (opt-in)
    "smart_detection_min_confidence": 0.7,  # Minimum confidence to show suggestion
    "smart_detection_min_album_size": 3,  # Minimum tracks to consider album
}
```

---

## 3. Task Breakdown

### Task #53: Backend - Context Detection Logic
**Estimated Time**: 1.5 hours
**Priority**: High
**Dependencies**: None

**Scope**:
- Implement `analyze_context()` function in `crate/core/context_detection.py` (new file)
- Album grouping by metadata
- Track number extraction and validation
- Sequential detection algorithm
- Classification logic with confidence scoring

**Tests**:
- Test album with complete tracks (1-12)
- Test album with gaps (1, 2, 4, 5)
- Test singles (no album tag)
- Test mixed albums in directory
- Test edge cases (1/12 format, non-numeric)

**Deliverable**: `crate/core/context_detection.py` with full test coverage

---

### Task #54: Backend - API Endpoint
**Estimated Time**: 1 hour
**Priority**: High
**Dependencies**: Task #53

**Scope**:
- Add `/api/analyze-context` endpoint to `web/main.py`
- Request/response models (Pydantic)
- Integration with context detection logic
- Error handling and timeouts
- Update `/api/load-directory` to include context (optional)

**Tests**:
- API endpoint integration tests
- Performance test (< 100ms for 1000 files)
- Error case handling

**Deliverable**: Working API endpoint with documentation

---

### Task #55: Frontend - Suggestion Banner UI
**Estimated Time**: 1.5 hours
**Priority**: High
**Dependencies**: Task #54

**Scope**:
- Create suggestion banner component in `web/static/index.html`
- CSS styling for banner (3 confidence states)
- JavaScript event handlers (Use/Ignore/Dismiss)
- Integration with file loading flow
- Local storage for "don't show again"

**Tests**:
- Manual UI testing (all 3 confidence levels)
- Responsive design testing
- Interaction testing (all buttons)

**Deliverable**: Functional suggestion banner

---

### Task #56: Frontend - Settings Integration
**Estimated Time**: 45 minutes
**Priority**: Medium
**Dependencies**: Task #55

**Scope**:
- Add smart detection toggle to Settings modal
- Update JavaScript load/save/reset handlers
- Feature flag check before showing suggestions
- Documentation in settings help text

**Tests**:
- Settings save/load
- Feature flag behavior (on/off)
- Default state (off)

**Deliverable**: Settings toggle working

---

### Task #57: Testing & Documentation
**Estimated Time**: 1 hour
**Priority**: High
**Dependencies**: Tasks #53-56

**Scope**:
- End-to-end testing (full workflow)
- Edge case verification (all 5 classifications)
- Performance benchmarking
- Documentation in `./claude/task-53-57-implementation.md`
- User guide update

**Tests**:
- Full workflow: Load directory → See suggestion → Accept → Rename
- Mixed albums test
- Singles test
- Disable feature test

**Deliverable**: Comprehensive test results and documentation

---

**Total Estimated Time**: 5.75 hours (~1 day)

---

## 4. Implementation Plan

### Phase 1: Backend (API First) - Tasks #53-54

**Step 1**: Create `crate/core/context_detection.py`
```python
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class ContextType(Enum):
    ALBUM = "ALBUM"
    PARTIAL_ALBUM = "PARTIAL_ALBUM"
    INCOMPLETE_ALBUM = "INCOMPLETE_ALBUM"
    SINGLES = "SINGLES"

@dataclass
class ContextAnalysis:
    type: ContextType
    confidence: float
    album_name: Optional[str]
    file_count: int
    suggested_templates: List[str]
    warnings: List[str]

def analyze_context(files: List[Dict]) -> List[ContextAnalysis]:
    """Analyze file metadata to detect album vs singles context."""
    pass  # Implementation
```

**Step 2**: Implement detection algorithm
- Group by album tag
- Extract and normalize track numbers
- Check sequential pattern
- Calculate confidence score
- Generate suggestions

**Step 3**: Add API endpoint
```python
@app.post("/api/analyze-context")
async def analyze_context_endpoint(files: List[FileInfo]) -> ContextAnalysisResponse:
    """Analyze file context and suggest templates."""
    pass  # Implementation
```

**Step 4**: Unit tests
```python
def test_album_detection_complete():
    files = [create_file(album="Test", track=str(i)) for i in range(1, 13)]
    result = analyze_context(files)
    assert result[0].type == ContextType.ALBUM
    assert result[0].confidence > 0.9

def test_singles_detection():
    files = [create_file(album="") for _ in range(10)]
    result = analyze_context(files)
    assert result[0].type == ContextType.SINGLES
```

### Phase 2: Frontend - Tasks #55-56

**Step 5**: Create suggestion banner HTML
```html
<div id="smart-suggestion-banner" class="smart-suggestion-banner hidden">
    <div class="suggestion-icon">💡</div>
    <div class="suggestion-content">
        <div class="suggestion-label">Smart Suggestion</div>
        <div class="suggestion-description" id="suggestion-description"></div>
        <div class="suggestion-template" id="suggestion-template"></div>
    </div>
    <div class="suggestion-actions">
        <button id="suggestion-use-btn" class="btn btn-primary btn-sm">Use This</button>
        <button id="suggestion-ignore-btn" class="btn btn-secondary btn-sm">Ignore</button>
        <button id="suggestion-dismiss-btn" class="btn-icon">×</button>
    </div>
</div>
```

**Step 6**: JavaScript integration
```javascript
async showSmartSuggestion(contextAnalysis) {
    if (!this.config.enable_smart_detection) return;

    const banner = document.getElementById('smart-suggestion-banner');
    const defaultContext = contextAnalysis.default_suggestion;

    // Populate banner
    document.getElementById('suggestion-description').textContent =
        `Detected: ${defaultContext.reason}`;
    document.getElementById('suggestion-template').textContent =
        defaultContext.template;

    // Show banner
    banner.classList.remove('hidden');

    // Event handlers
    document.getElementById('suggestion-use-btn').onclick = () => {
        this.applyTemplate(defaultContext.template);
        this.hideSuggestionBanner();
    };
}
```

**Step 7**: Settings integration
- Add toggle to HTML
- Update config load/save
- Feature flag checks

### Phase 3: Testing & Documentation - Task #57

**Step 8**: Integration testing
- Test complete workflow
- Performance benchmarking
- Edge case verification

**Step 9**: Documentation
- Implementation guide
- User guide update
- API documentation

### Phase 4: Rollout Strategy

**Feature Flag**:
- Default: `enable_smart_detection = False`
- Users opt-in via Settings
- Can disable at any time

**User Communication**:
- In-app tooltip on Settings toggle
- Help text explains feature
- No forced onboarding

**Monitoring**:
- Track adoption rate (% users enabling)
- Track suggestion acceptance rate
- Track confidence score distribution

---

## 5. Test Strategy

### 5.1 Unit Tests

**Backend (`test_context_detection.py`)**:
```python
class TestContextDetection:
    def test_complete_album(self):
        """Test album with tracks 1-12, same album tag"""

    def test_partial_album_with_gaps(self):
        """Test album with tracks 1,2,4,5,7 (gaps)"""

    def test_singles_no_album_tag(self):
        """Test files with no album metadata"""

    def test_mixed_albums(self):
        """Test directory with 2 different albums"""

    def test_track_format_variations(self):
        """Test '1', '01', '1/12' formats"""

    def test_performance_1000_files(self):
        """Verify < 100ms processing for 1000 files"""
```

**Frontend (`test_smart_suggestions.js`)**:
```javascript
describe('Smart Suggestions', () => {
    test('shows banner when feature enabled', () => {});
    test('hides banner when feature disabled', () => {});
    test('applies template on Use click', () => {});
    test('closes banner on Ignore click', () => {});
    test('persists dismiss on Dismiss click', () => {});
});
```

### 5.2 Integration Tests

**Full Workflow**:
1. Enable smart detection in Settings
2. Load directory with album (12 tracks)
3. Verify suggestion appears
4. Click "Use This"
5. Verify template applied
6. Generate preview
7. Execute rename
8. Verify track numbers in filenames

### 5.3 Edge Cases

| Scenario | Expected Behavior | Priority |
|----------|------------------|----------|
| Empty directory | No suggestion shown | Medium |
| Single file | Classify as single, no suggestion | Low |
| 2 files, same album | Classify as singles (< 3 min) | Medium |
| 3 files, sequential | Show album suggestion | High |
| 10 files, tracks 5-14 | Classify as partial album | High |
| Mixed albums (2 albums) | Show 2 separate suggestions | Medium |
| No metadata | Classify as singles | High |
| Track "A", "B", "C" | Classify as singles (non-numeric) | Low |
| 1000 files | Complete in < 100ms | High |

### 5.4 Performance Benchmarks

**Target Metrics**:
- Detection time: < 100ms for 1000 files
- UI render time: < 50ms
- Memory overhead: < 10MB
- API response time: < 150ms

**Test Data**:
- Small: 10 files, 1 album
- Medium: 100 files, 5 albums
- Large: 1000 files, 50 albums
- Extreme: 5000 files, 200 albums

---

## 6. Rollout Strategy

### 6.1 Feature Flag

**Default State**: OFF (opt-in)

**Rationale**:
- Preserves existing workflows
- Allows gradual adoption
- Reduces support burden for v1
- Users can test and provide feedback

### 6.2 User Onboarding

**No Forced Onboarding**:
- Feature appears in Settings
- Help text explains functionality
- Users discover organically or via release notes

**Optional Tooltip** (first load after update):
```
💡 New Feature: Smart Track Detection
Automatically suggests album vs single track formats.
Enable in Settings > Smart Track Detection
```

### 6.3 Monitoring & Feedback

**Metrics to Track**:
1. Adoption rate (% users enabling feature)
2. Suggestion acceptance rate (% clicked "Use This")
3. Suggestion dismissal rate (% clicked "Dismiss")
4. Average confidence score of shown suggestions
5. Performance metrics (detection time)

**Feedback Channels**:
- GitHub issues for bug reports
- User survey after 1 week of usage
- Analytics on suggestion acceptance patterns

### 6.4 Iteration Plan

**v1 (Initial Release)**:
- Basic album detection
- Single suggestion per directory
- Manual override always available

**v2 (Future Enhancement)**:
- Multiple context suggestions (mixed albums)
- Learning from user corrections
- Folder name analysis
- Preset suggestion (not just template)

**v3 (Advanced)**:
- Per-album template application
- Smart preset learning
- Context-aware variable inclusion

---

## 7. QA / Verification Checklist

### Design Quality
- [x] Detection heuristics are clearly specified with examples
- [x] UI design preserves user control (no forced automation)
- [x] API design follows existing patterns (API First)
- [x] Test strategy covers edge cases (mixed albums, no metadata, etc.)
- [x] Tasks are granular and estimable (< 2 hours each)
- [x] Documentation follows established format

### Implementation Readiness
- [x] Feature can be disabled by users who prefer manual mode
- [x] Backward compatible (existing templates still work)
- [x] Performance impact is minimal (< 100ms for detection)
- [x] Algorithm handles incomplete metadata gracefully
- [x] UI is non-blocking and contextual

### User Experience
- [x] Smart mode is opt-in (off by default)
- [x] Suggestions appear inline, easy to accept/reject
- [x] Users can always override or disable
- [x] Help text explains feature clearly
- [x] No forced onboarding or learning curve

### Technical Quality
- [x] API First approach (backend before frontend)
- [x] TDD ready (test cases specified)
- [x] Error handling defined
- [x] Performance benchmarks set
- [x] Monitoring plan exists

---

## 8. Assumptions Validated

1. ✅ **Album Detection**: Files grouped by album tag + sequential tracks
2. ✅ **Default Behavior**: OFF by default (matches research best practices)
3. ✅ **Suggestion Timing**: After directory load (co-pilot pattern)
4. ✅ **File Scope**: Analyzes all loaded files (respects current UX)
5. ✅ **Performance**: < 100ms target is achievable (simple heuristics)
6. ✅ **Metadata Only**: ID3 tags only in v1 (keeps scope manageable)

---

## 9. Research Sources

- [Beets Music Organizer](https://beets.io/) - Industry standard music library tool
- [MusicBrainz](https://musicbrainz.org/) - Open music metadata encyclopedia
- [Springer: Music Library Metadata Alignment](https://link.springer.com/article/10.1007/s00799-017-0223-9) - Academic research on metadata heuristics
- [GenAI UX Patterns](https://uxdesign.cc/20-genai-ux-patterns-examples-and-implementation-tactics-5b1868b7d4a1) - Co-pilot pattern design
- [Smart Interface Design Patterns](https://smart-interface-design-patterns.com/) - Autocomplete and suggestion UX

---

## 10. Next Steps

1. **Review & Approve**: Stakeholder review of design document
2. **Create Tasks**: Add Tasks #53-57 to task list via TaskCreate
3. **Begin Implementation**: Start with Task #53 (backend detection)
4. **Iterate**: Implement → Test → Document → Review cycle
5. **Deploy**: Feature flag off, deploy to production
6. **Monitor**: Track adoption and feedback
7. **Iterate v2**: Based on user feedback and usage patterns

---

**Document Status**: ✅ Complete
**Ready for Implementation**: Yes
**Estimated Completion**: 1-2 days of focused work
**Risk Level**: Low (feature flag, opt-in, backward compatible)
