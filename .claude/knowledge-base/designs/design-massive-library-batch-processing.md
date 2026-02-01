# Design: Batch Processing for Massive Libraries (50K+ Songs)

**Task**: #117
**Date**: 2026-01-31
**Status**: In Progress
**Priority**: HIGH

---

## Problem Statement

Current implementation cannot handle massive music libraries (50K+ songs) due to:

1. **Frontend Issues:**
   - Browser DOM: Renders all rows → 50K rows = browser crash
   - Memory: All file data held in memory → RAM exhaustion
   - Rendering: No virtual scrolling → UI freezes during render

2. **Backend Issues:**
   - Audio Analysis: Sequential processing → 28-56 hours for 50K files
   - Memory: All results buffered → 100-200MB for single operation
   - HTTP Timeout: Blocking calls → 30s timeout kills operations

3. **User Experience:**
   - No progress feedback during long operations
   - No way to cancel mid-operation effectively
   - No resume capability after interruption
   - Preview hangs for large directories

---

## Design Goals

1. **Scalability**: Handle 100K+ files without crashes
2. **Performance**: Complete operations in reasonable time (hours, not days)
3. **User Experience**: Clear progress, cancellable, resumable
4. **Resource Efficiency**: Batch processing, streaming, pagination
5. **Graceful Degradation**: Warn users, suggest alternatives

---

## Solution Architecture

### 1. Frontend: Pagination & Virtual Scrolling

**Current**: Render all 50K rows in DOM
**Solution**: Render only visible rows (virtual scrolling)

```javascript
// Virtual scrolling with react-window or custom implementation
class VirtualFileTable {
    constructor(files, rowHeight = 40) {
        this.files = files;           // Full file list
        this.rowHeight = rowHeight;
        this.visibleStart = 0;
        this.visibleEnd = 50;         // Show 50 rows at a time
        this.totalHeight = files.length * rowHeight;
    }

    onScroll(scrollTop) {
        this.visibleStart = Math.floor(scrollTop / this.rowHeight);
        this.visibleEnd = this.visibleStart + 50;
        this.renderVisibleRows();
    }

    renderVisibleRows() {
        // Only render rows [visibleStart, visibleEnd]
        const visibleFiles = this.files.slice(this.visibleStart, this.visibleEnd);
        // Update DOM with only these rows
    }
}
```

**Benefits:**
- DOM: 50 rows instead of 50K rows
- Memory: ~10MB instead of ~500MB
- Rendering: Instant instead of 10+ seconds

**Trade-offs:**
- Slightly more complex code
- Requires scroll position tracking

**Implementation:**
- Use `<div>` with fixed height container
- Calculate visible row range on scroll
- Render only visible rows with absolute positioning
- Update on scroll events (throttled to 16ms)

### 2. Backend: Streaming Responses

**Current**: Buffer all results, send at end
**Solution**: Stream results as they complete

```python
from fastapi.responses import StreamingResponse
import json

@app.post("/api/rename/execute-stream")
async def execute_rename_stream(request: ExecuteRenameRequest):
    """
    Stream rename results as they complete (Server-Sent Events).
    """
    async def event_generator():
        # Send initial event
        yield f"data: {json.dumps({'type': 'start', 'total': len(files)})}\n\n"

        # Process files and yield each result
        for i, file in enumerate(files):
            result = await process_file(file)
            yield f"data: {json.dumps({'type': 'progress', 'index': i, 'result': result})}\n\n"

        # Send completion event
        yield f"data: {json.dumps({'type': 'complete'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

**Frontend (EventSource)**:
```javascript
const eventSource = new EventSource('/api/rename/execute-stream');

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);

    switch (data.type) {
        case 'start':
            initProgressBar(data.total);
            break;
        case 'progress':
            updateProgress(data.index, data.result);
            break;
        case 'complete':
            showCompletionMessage();
            eventSource.close();
            break;
    }
};

eventSource.onerror = (error) => {
    console.error('Stream error:', error);
    eventSource.close();
};
```

**Benefits:**
- Real-time progress updates
- No memory buffering
- Can cancel via eventSource.close()

### 3. Backend: Parallel Audio Analysis

**Current**: Sequential audio analysis (1-2 files at a time)
**Solution**: Parallelize with worker pool

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def parallel_audio_analysis(files, max_workers=8):
    """
    Analyze multiple files in parallel.

    Args:
        files: List of file paths
        max_workers: Number of parallel workers (default: 8)

    Returns:
        Generator of (file_path, analysis_result) tuples
    """
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all files to worker pool
        future_to_file = {
            executor.submit(analyze_single_file, file): file
            for file in files
        }

        # Yield results as they complete
        for future in as_completed(future_to_file):
            file = future_to_file[future]
            try:
                result = future.result(timeout=30)  # 30s timeout per file
                yield (file, result)
            except Exception as exc:
                yield (file, {'error': str(exc)})

def analyze_single_file(file_path):
    """Analyze single file (BPM + Key detection)."""
    bpm = detect_bpm_from_audio(file_path)
    key = detect_key_from_audio(file_path)
    return {'bpm': bpm, 'key': key}
```

**Performance Improvement:**
- **Current**: 50K files @ 2s each = 100K seconds = 27.7 hours
- **8 Workers**: 50K files @ 2s / 8 workers = 12.5K seconds = 3.5 hours
- **Speedup**: 8x faster (near-linear scaling with CPU cores)

**Configuration**:
```python
# Auto-detect optimal workers
import multiprocessing
optimal_workers = min(8, multiprocessing.cpu_count())
```

### 4. Batch Processing with Checkpoints

**Current**: Process all files, lose progress on interruption
**Solution**: Process in batches, save checkpoints

```python
class BatchRenamer:
    def __init__(self, files, batch_size=1000, checkpoint_file=".crate_checkpoint.json"):
        self.files = files
        self.batch_size = batch_size
        self.checkpoint_file = checkpoint_file
        self.resume_from = 0

        # Load checkpoint if exists
        self.load_checkpoint()

    def load_checkpoint(self):
        """Load progress from checkpoint file."""
        if Path(self.checkpoint_file).exists():
            with open(self.checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                self.resume_from = checkpoint.get('processed_count', 0)
                logger.info(f"Resuming from file {self.resume_from}")

    def save_checkpoint(self, processed_count):
        """Save progress to checkpoint file."""
        with open(self.checkpoint_file, 'w') as f:
            json.dump({
                'processed_count': processed_count,
                'timestamp': time.time(),
                'total_files': len(self.files)
            }, f)

    def process_in_batches(self):
        """Process files in batches with checkpoints."""
        for batch_start in range(self.resume_from, len(self.files), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(self.files))
            batch = self.files[batch_start:batch_end]

            logger.info(f"Processing batch {batch_start}-{batch_end} of {len(self.files)}")

            # Process batch
            results = self.process_batch(batch)

            # Save checkpoint after each batch
            self.save_checkpoint(batch_end)

            # Yield results for streaming
            yield from results

    def process_batch(self, batch):
        """Process single batch of files."""
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(self.process_file, file) for file in batch]

            for future in as_completed(futures):
                yield future.result()
```

**Usage**:
```python
@app.post("/api/rename/execute-batch")
async def execute_batch_rename(request: ExecuteRenameRequest):
    """Execute rename with batch processing and checkpoints."""
    renamer = BatchRenamer(files, batch_size=1000)

    async def event_generator():
        for result in renamer.process_in_batches():
            yield f"data: {json.dumps(result)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Benefits:**
- Resume after interruption (power loss, crash)
- Progress persists across sessions
- User can pause/resume operations

### 5. Progressive Loading (Load-On-Demand)

**Current**: Load all 50K files metadata at once
**Solution**: Load initial batch, lazy-load rest

```javascript
class ProgressiveLoader {
    constructor(api, batchSize = 1000) {
        this.api = api;
        this.batchSize = batchSize;
        this.allFiles = [];
        this.loadedBatches = 0;
        this.totalFiles = 0;
    }

    async loadInitialBatch(directory) {
        // Load first batch only (1000 files)
        const response = await this.api.listDirectory(directory, {
            offset: 0,
            limit: this.batchSize
        });

        this.allFiles = response.files;
        this.totalFiles = response.total_count;
        this.loadedBatches = 1;

        return this.allFiles;
    }

    async loadNextBatch() {
        if (this.loadedBatches * this.batchSize >= this.totalFiles) {
            return []; // All loaded
        }

        const response = await this.api.listDirectory(directory, {
            offset: this.loadedBatches * this.batchSize,
            limit: this.batchSize
        });

        this.allFiles = this.allFiles.concat(response.files);
        this.loadedBatches++;

        return response.files;
    }

    async loadAllRemaining() {
        while (this.loadedBatches * this.batchSize < this.totalFiles) {
            await this.loadNextBatch();
        }
    }
}
```

**Benefits:**
- Fast initial load (1-2 seconds for first 1000 files)
- User can start working immediately
- Load rest in background

### 6. Warning System for Large Libraries

**Current**: No warning, just fails
**Solution**: Warn users and suggest alternatives

```python
@app.post("/api/directory/list")
async def list_directory(request: DirectoryRequest):
    """List files with warnings for large directories."""
    mp3_files = find_mp3s(dir_path, recursive=request.recursive)

    # Warn if too many files
    if len(mp3_files) > 25000:
        return {
            "files": mp3_files[:1000],  # Return first 1000
            "total_count": len(mp3_files),
            "truncated": True,
            "warning": {
                "level": "critical",
                "message": f"Found {len(mp3_files)} files. This may overwhelm the browser.",
                "suggestions": [
                    "Use CLI instead of web GUI for massive libraries",
                    "Load subdirectories individually",
                    "Enable batch processing mode (coming soon)"
                ]
            }
        }
    elif len(mp3_files) > 10000:
        return {
            "files": mp3_files,
            "total_count": len(mp3_files),
            "warning": {
                "level": "warning",
                "message": f"Found {len(mp3_files)} files. Performance may be slow.",
                "suggestions": [
                    "Consider using CLI for better performance",
                    "Disable audio analysis for preview"
                ]
            }
        }
    else:
        return {
            "files": mp3_files,
            "total_count": len(mp3_files)
        }
```

**Frontend Display**:
```javascript
if (response.warning) {
    const level = response.warning.level;  // 'critical' or 'warning'
    const message = response.warning.message;
    const suggestions = response.warning.suggestions;

    this.ui.showWarningBanner(level, message, suggestions);
}
```

---

## Implementation Plan

### Phase 1: Backend Parallelization (Week 1)
1. Implement parallel audio analysis (Task #117a)
2. Add batch processing with checkpoints (Task #117b)
3. Add streaming responses (Server-Sent Events) (Task #117c)
4. Test with 50K file library

### Phase 2: Frontend Pagination (Week 2)
1. Implement virtual scrolling for file table (Task #117d)
2. Add progressive loading (load-on-demand) (Task #117e)
3. Update UI to show batch progress
4. Test with 100K file library

### Phase 3: Warning System (Week 3)
1. Add file count warnings (Task #117f)
2. Add performance mode toggle (disable audio analysis)
3. Create CLI migration guide
4. User acceptance testing

---

## Performance Targets

| Library Size | Current Time | Target Time | Improvement |
|---|---|---|---|
| 10K files | 2-3 minutes | 30 seconds | 4-6x faster |
| 50K files | 10-15 minutes (web fails) | 3-5 minutes | ∞ (currently fails) |
| 100K files | N/A (fails) | 10-15 minutes | ∞ (currently fails) |

**Audio Analysis (50K files)**:
- Current: 27.7 hours (sequential)
- Target: 3.5 hours (8 workers)
- Improvement: 8x faster

---

## Testing Strategy

### Unit Tests
- Test batch processing with 1000 files
- Test checkpoint save/load
- Test parallel audio analysis
- Test virtual scrolling calculations

### Integration Tests
- Load 50K file directory
- Process 10K file rename with checkpoints
- Resume after simulated crash
- Cancel mid-operation

### Performance Tests
- Benchmark parallel vs sequential audio analysis
- Measure DOM memory usage (virtual scrolling vs full render)
- Stress test with 100K files

### User Acceptance Tests
- DJ with 50K+ song library
- Test resume after interruption
- Test CLI vs web performance comparison

---

## Edge Cases & Failure Modes

### Edge Case 1: Checkpoint Corruption
**Scenario**: Checkpoint file corrupted during write
**Solution**: Write to temp file, then atomic rename

### Edge Case 2: Partial Batch Failure
**Scenario**: 5 files in batch of 1000 fail
**Solution**: Continue batch, log failures, include in results

### Edge Case 3: Memory Pressure
**Scenario**: System low on RAM during processing
**Solution**: Reduce batch size dynamically, warn user

### Edge Case 4: Network Interruption
**Scenario**: Web GUI loses connection mid-stream
**Solution**: EventSource auto-reconnects, resume from checkpoint

---

## Rollback Plan

### Feature Flag
```python
# config.py
DEFAULT_CONFIG = {
    "enable_batch_processing": False,  # Off by default
    "batch_size": 1000,                # Configurable
    "parallel_workers": 8,              # Configurable
}
```

### Fallback
- If batch processing fails, fall back to sequential mode
- If streaming fails, fall back to buffered response
- If virtual scrolling fails, show pagination controls

---

## Status

✅ **Design Complete**
⏳ **Implementation**: Ready to start
📋 **Next Steps**: Implement Phase 1 (backend parallelization)

**Estimated Implementation Time**: 3 weeks
**Testing Time**: 1 week
**Total**: 4 weeks to production

---

**Task #117 Status**: Design complete, ready for implementation approval
