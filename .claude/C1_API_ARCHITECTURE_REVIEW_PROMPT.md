# TASK C1: API Architecture Review

**Date**: 2026-01-28
**Priority**: MEDIUM
**Estimated**: 2 hours
**TWO-PHASE**: This is the improved prompt (Phase 1)

---

## IMPROVED PROMPT - C1: API Architecture Review

**Role**: Senior API Architect + System Design Expert

**Objective**: Conduct comprehensive review of the current API architecture to identify gaps, verify completeness, and ensure it's ready for web UI integration. This review ensures the API-First architecture is solid before building the web frontend.

**Context**:
- Project uses API-First architecture (Netflix-style separation)
- TUI layer currently uses the API
- Web UI will be built on top of same API
- API must be complete, robust, and well-designed
- All business logic must be accessible via API

---

## REVIEW SCOPE

### Areas to Review

#### 1. **API Completeness** (HIGH PRIORITY)
- Does API expose ALL functionality needed for web UI?
- Are there any features only available in TUI/CLI?
- Can web UI replicate 100% of TUI functionality via API?
- Are all config operations accessible?
- Are all metadata operations accessible?

#### 2. **Endpoint Coverage** (HIGH PRIORITY)
- List all current API endpoints/methods
- Identify missing endpoints for web UI needs
- Check if cancellation is supported
- Check if progress tracking is supported
- Check if preview/dry-run is supported

#### 3. **Data Models** (MEDIUM PRIORITY)
- Are request/response models well-defined?
- Are models documented with type hints?
- Are models serializable (JSON-friendly)?
- Are models versioned for compatibility?

#### 4. **Error Handling** (HIGH PRIORITY)
- How are errors communicated to API clients?
- Are error messages user-friendly?
- Are error codes consistent?
- Can web UI distinguish error types?

#### 5. **State Management** (HIGH PRIORITY)
- How is operation state tracked?
- Can multiple operations run concurrently?
- How is progress reported to clients?
- How is cancellation handled?

#### 6. **Thread Safety** (MEDIUM PRIORITY)
- Is API thread-safe for concurrent requests?
- Are there any race conditions?
- Is ReservationBook pattern used correctly?

#### 7. **API Design Patterns** (MEDIUM PRIORITY)
- Does API follow REST principles (if HTTP)?
- Are naming conventions consistent?
- Is API intuitive to use?
- Are there any anti-patterns?

---

## REVIEW METHODOLOGY

### Step 1: Document Current API Surface

Create comprehensive documentation of current API:

```markdown
# Current API Surface - DJ MP3 Renamer

## Main API Class: `RenamerAPI`

### Constructor
```python
RenamerAPI(workers: int = 4, logger: Optional[logging.Logger] = None)
```

### Public Methods

#### rename_files()
```python
def rename_files(self, request: RenameRequest) -> RenameStatus
```
- **Purpose**: Execute rename operation
- **Input**: RenameRequest (path, recursive, dry_run, template, progress_callback, etc.)
- **Output**: RenameStatus (total, renamed, skipped, errors)
- **State**: Synchronous, blocking call
- **Cancellation**: Via progress_callback raising exception
- **Progress**: Via progress_callback(count, filename)

[Document ALL methods...]
```

### Step 2: Identify Web UI Requirements

Based on mac-maintenance analysis and modern web UI patterns:

**Required API Capabilities:**
1. ✅ Start rename operation
2. ✅ Dry-run/preview mode
3. ⚠️ Get operation status (polling support?)
4. ⚠️ Cancel operation (thread-safe cancel?)
5. ✅ Progress updates
6. ❓ List files before rename (preview file list?)
7. ❓ Get config values (exposed via API?)
8. ❓ Set config values (exposed via API?)
9. ❓ Validate template (before running?)
10. ❓ Get metadata for single file (preview?)

### Step 3: Gap Analysis

Compare current API vs. web UI requirements:

**Gaps Found:**
1. **No async status polling**: Web UI needs to poll for status
   - Current: Blocking synchronous call
   - Needed: Non-blocking with status endpoint

2. **No thread-safe cancellation**: progress_callback exception pattern not web-friendly
   - Current: Exception in callback
   - Needed: Separate cancel() method

3. **No file list preview**: Web UI can't show "these files will be renamed"
   - Current: Must run dry-run to discover
   - Needed: list_files() method

[Document all gaps...]

### Step 4: Recommendations

For each gap, provide recommendation:

**Gap 1: Async Operation Support**
```python
# Recommendation: Add operation ID pattern

class RenamerAPI:
    def start_rename(self, request: RenameRequest) -> str:
        """
        Start rename operation asynchronously.

        Returns:
            Operation ID for status tracking
        """
        operation_id = generate_uuid()
        # Start operation in background thread
        # Store operation state in _operations dict
        return operation_id

    def get_status(self, operation_id: str) -> OperationStatus:
        """
        Get status of running operation.

        Returns:
            OperationStatus with progress, current_file, etc.
        """
        pass

    def cancel_operation(self, operation_id: str) -> bool:
        """
        Cancel running operation.

        Returns:
            True if cancelled, False if already complete
        """
        pass
```

**Gap 2: File List Preview**
```python
def list_files(self, request: RenameRequest) -> List[FilePreview]:
    """
    List files that would be renamed.

    Returns:
        List of FilePreview objects showing old -> new names
    """
    pass
```

[Recommend solutions for all gaps...]

---

## DELIVERABLES

### 1. API Architecture Review Document

Create: `.claude/C1_API_ARCHITECTURE_REVIEW_RESULTS.md`

**Sections:**
1. **Executive Summary**
   - Overall API health: Good/Fair/Poor
   - Major gaps found: Count and severity
   - Readiness for web UI: Ready/Needs Work/Major Overhaul

2. **Current API Surface**
   - Complete documentation of all public methods
   - Request/response models
   - State management approach

3. **Gap Analysis**
   - List of gaps with severity (HIGH/MEDIUM/LOW)
   - Impact on web UI for each gap
   - Workarounds if any

4. **Recommendations**
   - Prioritized list of improvements
   - Code examples for each recommendation
   - Estimated effort for each

5. **API Design Evaluation**
   - Strengths of current design
   - Weaknesses of current design
   - Compliance with API-First principles

### 2. API Enhancement Backlog

Create: `.claude/C1_API_ENHANCEMENT_BACKLOG.md`

**Format:**
```markdown
# API Enhancement Backlog

## HIGH Priority (Blocking Web UI)
- [ ] ENH-001: Add async operation support with operation IDs
      - Estimate: 4 hours
      - Impact: Critical for web UI polling
      - Files: api/renamer.py, api/models.py

- [ ] ENH-002: Add thread-safe cancel() method
      - Estimate: 2 hours
      - Impact: Critical for cancel button
      - Files: api/renamer.py

[List all high priority items...]

## MEDIUM Priority (Improves UX)
[List medium priority items...]

## LOW Priority (Nice to Have)
[List low priority items...]
```

---

## EVALUATION CRITERIA

### API Completeness Checklist

- [ ] All TUI functionality accessible via API
- [ ] No business logic in UI layers
- [ ] Config management exposed via API
- [ ] Metadata operations exposed via API
- [ ] File operations exposed via API
- [ ] Validation operations exposed via API

### Web UI Readiness Checklist

- [ ] Can start operations asynchronously
- [ ] Can poll for operation status
- [ ] Can cancel running operations
- [ ] Can preview changes before applying
- [ ] Can track progress in real-time
- [ ] Can handle errors gracefully
- [ ] Can access all config options

### API Design Quality Checklist

- [ ] Methods have clear, consistent naming
- [ ] Parameters use type hints
- [ ] Return values are well-defined
- [ ] Errors are properly typed
- [ ] Documentation is complete
- [ ] API is intuitive to use
- [ ] API follows SOLID principles
- [ ] API is testable

---

## CURRENT API FILES TO REVIEW

Based on codebase structure:

### Primary API Files
- `dj_mp3_renamer/api/renamer.py` - Main RenamerAPI class
- `dj_mp3_renamer/api/models.py` - Request/response models

### Supporting Modules (Check API Exposure)
- `dj_mp3_renamer/core/config.py` - Config management
- `dj_mp3_renamer/core/io.py` - File operations
- `dj_mp3_renamer/core/validation.py` - Validation
- `dj_mp3_renamer/core/metadata_parsing.py` - Metadata
- `dj_mp3_renamer/core/template.py` - Template expansion
- `dj_mp3_renamer/core/audio_analysis.py` - Audio analysis

### UI Layers (Should Only Use API)
- `dj_mp3_renamer/tui/app.py` - Check if using API correctly
- `dj_mp3_renamer/cli/main.py` - Check if using API correctly

---

## ANALYSIS APPROACH

### 1. Code Reading
- Read all API files thoroughly
- Document every public method
- Note all request/response models
- Identify dependencies

### 2. Usage Analysis
- Review how TUI uses API
- Review how CLI uses API
- Identify patterns and anti-patterns
- Note any direct core module access (API bypass)

### 3. Gap Identification
- Compare API surface vs. web UI needs
- Identify missing functionality
- Prioritize gaps by severity

### 4. Recommendation Development
- Design solutions for each gap
- Provide code examples
- Estimate implementation effort
- Consider backward compatibility

---

## ACCEPTANCE CRITERIA

- [ ] Complete API surface documented in review results
- [ ] All gaps identified with severity ratings
- [ ] Recommendations provided for each gap
- [ ] Enhancement backlog created with effort estimates
- [ ] Executive summary rates API readiness for web UI
- [ ] Review results committed to `.claude/` directory
- [ ] No code changes in this task (review only)

---

## VERIFICATION COMMANDS

```bash
# Read API files
cat dj_mp3_renamer/api/renamer.py
cat dj_mp3_renamer/api/models.py

# Check how TUI uses API
grep -n "RenamerAPI" dj_mp3_renamer/tui/app.py

# Check how CLI uses API
grep -n "RenamerAPI" dj_mp3_renamer/cli/main.py

# Count public methods
grep "def [a-z]" dj_mp3_renamer/api/renamer.py | wc -l
```

---

## EXPECTED OUTCOMES

### Best Case Scenario
- API is complete and ready for web UI
- Minor gaps only (LOW priority)
- No major refactoring needed
- Can proceed directly to web UI implementation

### Likely Scenario
- API is mostly complete
- Some gaps for async/polling support (HIGH priority)
- Need to add a few helper methods (MEDIUM priority)
- 2-4 hours of API enhancements needed before web UI

### Worst Case Scenario
- Major API gaps found
- Significant refactoring needed
- Business logic found in UI layers
- Need to redesign API before web UI

---

## CONSTRAINTS

1. **No Code Changes**: This is a review/analysis task only
2. **Focus on Web UI**: Prioritize gaps that block web UI
3. **API-First Principle**: Ensure all logic is in API, not UI
4. **Backward Compatibility**: Recommendations must not break TUI/CLI
5. **Realistic Estimates**: Provide honest effort estimates

---

## BEST PRACTICES (2025-2026)

### API Design Patterns
- **Operation ID Pattern**: For long-running operations
- **Status Endpoint Pattern**: For polling progress
- **Cancel Endpoint Pattern**: For graceful cancellation
- **Idempotency**: Safe to retry failed operations
- **Versioning**: API version in requests (future-proof)

### Modern API Standards
- **Type Hints**: Full type coverage for IDE support
- **Pydantic Models**: Validated request/response models
- **OpenAPI/Swagger**: Auto-generated API docs (future)
- **Rate Limiting**: Protect against abuse (future)
- **CORS Support**: For web clients (future)

---

## ASSUMPTIONS

1. Current API is in `dj_mp3_renamer/api/` directory
2. TUI and CLI are thin wrappers around API
3. Web UI will use same API as TUI/CLI
4. API must support concurrent operations
5. Python 3.8+ type hints are available

---

## PHASE 2: EXECUTION READY

This improved prompt is ready for execution. Proceed with comprehensive API architecture review.
