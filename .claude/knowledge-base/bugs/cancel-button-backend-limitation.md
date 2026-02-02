# Cancel Button Backend Limitation

**Date**: 2026-02-01
**Status**: FIXED (v20260201-05)

## Issue

When user clicks Cancel during metadata loading:
- ✅ Frontend stops sending new HTTP requests
- ❌ Backend continues processing already-started requests
- ❌ Files continue to be modified (BPM/Key saved to disk)

## Root Cause

Each `/api/file/metadata` request does expensive work:
1. MusicBrainz lookup (~1-2s)
2. Audio analysis (~2-5s)  
3. BPM detection (~1-3s)
4. Key detection (~1-3s)
5. **Write to disk** (modifies MP3 file)

The backend FastAPI endpoint doesn't check for client disconnection during these operations.

## User Impact

**Severe UX Issue**:
- User clicks Cancel expecting immediate stop
- Backend keeps running for minutes (63 files × ~10s = 10+ minutes)
- Files are being modified without user awareness
- User thinks operation stopped but it didn't

## Workaround (Short-term)

**Option 1**: Add warning before loading
- "Loading metadata will analyze and modify 63 files. This cannot be cancelled once started."
- Make user confirm before starting

**Option 2**: Batch processing with checkpoints
- Process files in batches of 10
- Check for cancellation between batches
- User can cancel between batches

**Option 3**: Read-only metadata loading
- Don't write BPM/Key to disk during initial load
- Only write when user clicks "Rename Now"
- Makes cancel actually work (no side effects)

## Long-term Fix

Add cancellation points in backend:
```python
async def analyze_file(path, request: Request):
    # Check if client disconnected
    if await request.is_disconnected():
        raise HTTPException(499, "Client disconnected")
    
    # MusicBrainz lookup
    metadata = await lookup_musicbrainz(path)
    
    # Check again
    if await request.is_disconnected():
        raise HTTPException(499, "Client disconnected")
    
    # Audio analysis
    audio = analyze_audio(path)
    
    # etc...
```

## Implementation (v20260201-05)

**Solution Implemented**: Option 1 - Make metadata loading read-only

**Changes Made**:
1. Added `write_metadata: bool = False` to `DirectoryRequest` model (web/main.py:34)
2. Updated `/api/file/metadata` endpoint to accept and pass through write_metadata parameter (web/main.py:407)
3. Modified `analyze_file()` to accept `write_tags: bool = False` parameter (crate/api/renamer.py:1007)
4. Existing `_enhance_metadata()` already had write_tags parameter support (crate/api/renamer.py:245)

**Result**:
- ✅ Metadata loading is now read-only by default (no disk writes)
- ✅ Cancel button works immediately with no side effects
- ✅ BPM/Key still written during actual rename operation (write_tags=True in _rename_one)
- ✅ User can cancel without worrying about files being modified

**Code Flow**:
```
Initial metadata load:
  Frontend → /api/file/metadata (write_metadata=False)
           → analyze_file(write_tags=False)
           → _enhance_metadata(write_tags=False)
           → No disk writes ✅

Rename operation:
  Frontend → /api/rename/execute
           → _rename_one()
           → _derive_target(write_tags=True)
           → _enhance_metadata(write_tags=True)
           → Writes BPM/Key to disk ✅
```

## Related

- Task #122: Made preview read-only (same pattern used here)
- Auto-preview threshold (200 files) prevents expensive operations for large libraries
