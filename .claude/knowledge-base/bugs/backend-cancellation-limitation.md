# Backend Cancellation Implementation

**Date**: 2026-02-01
**Status**: ✅ IMPLEMENTED - Cancellation between checkpoints

**Update**: Backend now supports cancellation! Uses threading.Event to check cancellation between expensive operations.

## How It Works Now (v20260201-12)

**Implementation**: Thread-based cancellation with checkpoints

1. **Frontend**: Clicks Cancel → aborts AbortController → closes HTTP connections
2. **Backend Endpoint**: Detects disconnect via `await request.is_disconnected()`
3. **Cancellation Signal**: Sets `threading.Event()` to signal background thread
4. **Backend Analysis**: Checks event between operations:
   - ✅ Before MusicBrainz lookup (~2s operation)
   - ✅ Before audio analysis (~8s operation)
5. **Graceful Stop**: Raises `OperationCancelled` exception at next checkpoint

**Worst Case Latency**:
- Cancelled during MusicBrainz: ~2s wasted
- Cancelled during audio analysis: ~8s wasted
- **No longer processes all files** - stops at next checkpoint!

**Files Modified**:
- `crate/api/renamer.py`: Added `cancel_event` parameter, cancellation checks
- `web/main.py`: Added `asyncio.to_thread()` with periodic disconnect checks
- `web/static/js/app.js`: Preview cell cleanup (already working)

---

## Original Issue (Pre-Fix)

Cancel button stops frontend from sending NEW requests, but backend continues processing requests that are already in-flight.

## Root Cause

**Synchronous Backend Code Blocks Event Loop**

The metadata analysis pipeline is synchronous:
```python
def analyze_file(file_path):  # Synchronous
    meta = read_mp3_metadata(file_path)  # Blocks
    lookup_acoustid(file_path)  # Blocks ~2s
    auto_detect_metadata(file_path)  # Blocks ~8s
    return enhanced_metadata
```

**Why Cancellation Doesn't Work:**
1. FastAPI endpoint is async
2. It calls sync `analyze_file()` which blocks the event loop
3. While blocked, no async operations (including disconnect checks) can run
4. Request completes before we can check if client disconnected

**Attempted Solutions That Failed:**
- ❌ `asyncio.run_coroutine_threadsafe()` - Causes deadlock in same event loop
- ❌ Periodic disconnect checks - Sync code blocks, can't check
- ❌ Shared cancellation flag - Can't update while sync code runs

## Current Behavior

**What Works:**
- ✅ Frontend stops sending new requests immediately
- ✅ Preview cells clear to "—" when cancelled
- ✅ Requests queued but not started are skipped

**What Doesn't Work:**
- ❌ Request currently processing completes (~10s)
- ❌ Backend keeps working even though frontend cancelled

**Impact:**
- User cancels after file #3
- File #4 is processing → Completes (~10s wasted)
- Files #5-63 never start ✅

## Why This Is Hard To Fix

**The Sync/Async Impedance Mismatch:**
- FastAPI is async (non-blocking)
- Music analysis libraries (librosa, acoustid) are sync (blocking)
- Can't check cancellation while sync code runs
- Refactoring to async requires changing ALL backend code

## Solutions

### Option 1: Accept Limitation (Current)
**Effort:** None
**Result:** 1 file (~10s) wasted per cancel

Document clearly:
- "Cancel stops new requests immediately"
- "Current file will finish processing (~10s)"

### Option 2: Run Sync Code in Thread Pool
**Effort:** Medium (1-2 days)
**Result:** Can cancel between checkpoints

```python
import concurrent.futures

executor = concurrent.futures.ThreadPoolExecutor()

@app.post("/api/file/metadata")
async def get_file_metadata(request):
    # Run sync code in thread pool
    future = executor.submit(analyze_file, file_path)

    # Periodically check for cancellation
    while not future.done():
        if await http_request.is_disconnected():
            future.cancel()  # May not stop immediately
            raise HTTPException(499, "Cancelled")
        await asyncio.sleep(0.1)

    return future.result()
```

**Limitations:**
- Can only cancel between operations, not during
- Still ~10s delay if cancelled mid-analysis

### Option 3: Refactor to Full Async (Best Long-term)
**Effort:** High (1-2 weeks)
**Result:** Immediate cancellation

Convert entire backend to async:
```python
async def analyze_file_async(file_path, http_request):
    meta = await read_mp3_metadata_async(file_path)

    if await http_request.is_disconnected():
        raise OperationCancelled()

    mb_data = await lookup_acoustid_async(file_path)

    if await http_request.is_disconnected():
        raise OperationCancelled()

    audio_data = await auto_detect_metadata_async(file_path)

    return enhanced_metadata
```

**Challenges:**
- Most audio libraries are sync-only (librosa, acoustid)
- Would need to wrap in `asyncio.to_thread()` or find async alternatives
- Large refactor touching many files

## Recommendation

**For v1.0:** Accept Option 1 limitation, document clearly

**For v2.0:** Implement Option 2 (thread pool with periodic checks)

**For v3.0:** Consider Option 3 if performance issues arise

## Related

- `.claude/knowledge-base/bugs/cancel-button-backend-limitation.md` - Initial analysis
- Task #133: Read-only metadata loading (implemented)
- Frontend cancel works perfectly (stops new requests)
- Issue is purely backend architecture

## Lessons Learned

1. **Always check sync/async compatibility early** in architecture phase
2. **Sync code in async context = no cancellation** without threads
3. **Audio processing libraries are mostly sync** (2026 state)
4. **Honest limitations > broken promises** in UX
5. **Document tradeoffs clearly** for future decisions
