# Lessons Learned

**Purpose**: Document every mistake, bug, or "aha!" moment so we never repeat them. This file grows over time and becomes institutional knowledge.

**Format**: Each entry should include date, problem, root cause, solution, and prevention strategy.

---

## How to Use This File

### When to Add an Entry
- Fixed a bug → Document what caused it and how to prevent it
- Made a wrong technology choice → Document why and what to choose instead
- Discovered a gotcha or edge case → Document it
- Learned a best practice → Document it
- Spent > 30 minutes on something that should have been simple → Document why

### Entry Template
```markdown
## [YYYY-MM-DD] Brief Title

**Context**: What were we trying to do?

**Problem**: What went wrong?

**Root Cause**: Why did it happen?

**Solution**: How did we fix it?

**Prevention**: How do we avoid this in the future?

**Related Files**: `path/to/file.py:123`

**Tags**: #security #api #testing #architecture
```

---

## Lessons

### [2026-02-01] Template Initialization

**Context**: Creating reusable Claude Code project template

**Problem**: Needed to consolidate multiple prompt systems and best practices into single coherent framework

**Solution**:
- Research official Claude Code documentation
- Created `.claude/` structure with knowledge-base, state, workflows, templates
- Wrote comprehensive CLAUDE.md as main system prompt
- Separated concerns: workflows vs knowledge vs state

**Prevention**: Always start new projects by copying this template structure

**Tags**: #meta #template #initialization

---

### Common Anti-Patterns to Avoid

#### 1. Repository Cleanup Gone Wrong
**Problem**: Running "cleanup" that deletes working development tools (like .venv)

**Prevention**:
- "Repository cleanup for GitHub" means preventing unwanted files from being pushed, not deleting local files
- Use .gitignore for exclusion, not deletion
- Never delete: .venv, node_modules, .env (add to .gitignore instead)

**Tags**: #git #cleanup

---

#### 2. Editing Before Reading
**Problem**: Making changes to files without reading them first

**Prevention**:
- ALWAYS read affected files before editing
- Understand existing patterns before adding new code
- Check for edge cases and existing error handling

**Tags**: #workflow #code-quality

---

#### 3. Testing at the End
**Problem**: Writing all implementation code first, then trying to test it

**Prevention**:
- Follow TDD strictly: test first, then implement
- Test after every change, not just at the end
- Catch regressions early when they're cheap to fix

**Tags**: #testing #tdd

---

#### 4. Stale Documentation
**Problem**: Not updating .claude/ files immediately, leading to lost context later

**Prevention**:
- Update `.claude/state/current-state.md` after EVERY session
- Add to lessons-learned.md as soon as you learn something
- "I'll remember" is a lie - write it down now

**Tags**: #documentation #memory

---

#### 5. Unmaintained Dependencies
**Problem**: Choosing libraries without checking maintenance status, causing issues later

**Prevention**:
- Before adding dependency, check: last commit date, issue response time, GitHub stars/forks
- Research "best [library] 2026" to find current recommendations
- Prefer actively maintained projects
- Check Stack Overflow for common issues

**Tags**: #dependencies #research

---

### [2026-02-01] Cancel Button - Setting Controller to Null

**Context**: Implementing cancel functionality for metadata loading (Task #126-127)

**Problem**: Cancel button was clicked, frontend cleanup ran, but the renderFileList loop never stopped. All 63 files continued being processed despite cancel signal.

**Root Cause**:
```javascript
// In cancelMetadataLoading():
this.metadataAbortController.abort();      // Sets signal.aborted = true
this.metadataAbortController = null;       // ← BUG!

// In renderFileList() loop:
if (this.metadataAbortController && this.metadataAbortController.signal.aborted) {
    // ↑ This check FAILS because controller is now null!
    break;  // Never executes
}
```

The cancel handler set the controller to `null` immediately after aborting it, so the loop's check for `signal.aborted` always evaluated to false (null check failed first).

**Solution**:
1. Call `.abort()` to set signal.aborted = true
2. Do NOT set to null in cancel handler
3. Let the loop check signal.aborted and break
4. Let finally block set controller to null after loop finishes

```javascript
// FIXED: cancelMetadataLoading()
this.metadataAbortController.abort();  // Signal cancellation
// Don't set to null here!
this.hideMetadataProgress();

// Controller will be set to null in renderFileList's finally block
```

**Prevention**:
- AbortController should remain alive until checked by the code that's using it
- Only clean up (set to null) AFTER all checks are complete
- Consider the lifecycle: create → abort → check → cleanup
- Never clean up shared state until all consumers are done with it

**Related Files**:
- `web/static/js/app.js:1542-1591` (cancel handlers)
- `web/static/js/app.js:951-1011` (renderFileList loop)

**Tags**: #frontend #cancellation #async #timing #lifecycle

---

### [2026-02-01] Backend Cancellation with Threading.Event

**Context**: Backend continued processing all files after frontend cancelled requests

**Problem**: Even with frontend cancel working, backend processed all 63 files. Each HTTP request is independent, so cancellation didn't persist across requests.

**Root Cause**:
- Each `/api/file/metadata` request got its own `cancel_event`
- Frontend cancelled request #2, but request #3 started fresh with no cancellation
- Backend synchronous code (MusicBrainz ~2s, audio analysis ~8s) blocks event loop
- Can't check `await request.is_disconnected()` while sync code runs

**Solution**:
1. Added `cancel_event: threading.Event` parameter to `analyze_file()` and `_enhance_metadata()`
2. Check `cancel_event.is_set()` before each expensive operation:
   - Before MusicBrainz lookup (~2s)
   - Before audio analysis (~8s)
3. Use `asyncio.to_thread()` to run sync code in background
4. Periodically check `await request.is_disconnected()` every 100ms
5. Set cancel_event when disconnect detected
6. Raise `OperationCancelled` at next checkpoint

**Result**: Only 1 file completes after cancel (the one in-flight), not all 63!

**Prevention**:
- For long-running sync operations, add cancellation checkpoints between operations
- Use threading.Event for thread-safe cancellation signaling
- Run sync code in thread pool via asyncio.to_thread() to allow async checks
- Check cancellation BEFORE expensive operations, not during
- Accept that current operation may complete (~2-8s delay), but prevent ALL subsequent operations

**Related Files**:
- `crate/api/renamer.py:1007-1062` (analyze_file with cancel_event)
- `crate/api/renamer.py:245-300` (_enhance_metadata with cancellation checks)
- `web/main.py:408-475` (endpoint with periodic disconnect checks)

**Tags**: #backend #cancellation #async #threading #sync-async-bridge

---

## Category Index

### Security
- [Link to security-related lessons as they're added]

### API Design
- [Link to API-related lessons as they're added]

### Testing
- [2026-02-01] Testing at the End (see above)

### Architecture
- [2026-02-01] Template Initialization (see above)

### Git/Version Control
- [2026-02-01] Repository Cleanup Gone Wrong (see above)

### Performance
- [Link to performance-related lessons as they're added]

### UI/UX
- [Link to UI/UX-related lessons as they're added]

---

## Statistics

- **Total Lessons**: 7
- **Last Updated**: 2026-02-01
- **Most Common Tags**: #testing, #git, #documentation, #frontend, #backend, #cancellation

---

*This file should grow continuously. A healthy project will have dozens to hundreds of entries over time. If this file isn't growing, we're not learning.*
