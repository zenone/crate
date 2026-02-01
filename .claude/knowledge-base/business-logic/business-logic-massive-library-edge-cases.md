# Business Logic: Massive Library Edge Cases

**Task**: #119
**Date**: 2026-01-31
**Status**: In Progress
**Priority**: HIGH

---

## Overview

This document identifies and proposes solutions for all business logic edge cases when handling massive music libraries (50K+ songs).

---

## Edge Case Categories

1. **Per-Album Detection Edge Cases**
2. **Metadata Conflict Edge Cases**
3. **File System Edge Cases**
4. **Performance Edge Cases**
5. **User Workflow Edge Cases**

---

## 1. Per-Album Detection Edge Cases

### Edge Case 1.1: Flat Directory with Album Metadata

**Scenario**:
```
/Music/
  ├─ song1.mp3 (album: "The White Album")
  ├─ song2.mp3 (album: "The White Album")
  ├─ song3.mp3 (album: "Revolver")
  └─ song4.mp3 (album: "Revolver")
```

**Current Behavior**: Single-banner mode (all files in same directory)
**Expected**: 2 album groups (White Album, Revolver)

**Solution**: Hybrid detection (directory + album metadata)

```python
def group_files_hybrid(directory: str, files: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Group files by subdirectory OR album metadata (whichever provides more groups).

    Strategy:
    1. Try grouping by subdirectory
    2. Try grouping by album metadata
    3. Use whichever produces more distinct groups (better granularity)
    """

    # Method 1: Group by subdirectory
    dir_groups = group_files_by_subdirectory(directory, files)

    # Method 2: Group by album metadata
    album_groups = defaultdict(list)
    for file in files:
        album_name = file.get('metadata', {}).get('album', '[No Album]')
        album_groups[album_name].append(file)

    # Choose method with more groups (better granularity)
    if len(album_groups) > len(dir_groups):
        logger.info(f"Using album metadata grouping ({len(album_groups)} groups vs {len(dir_groups)} directory groups)")
        return dict(album_groups)
    else:
        logger.info(f"Using directory grouping ({len(dir_groups)} groups)")
        return dir_groups
```

**Trade-offs**:
- Pro: Works for flat directories with album tags
- Con: May group differently than expected if metadata inconsistent
- Decision: Use hybrid, log which method used, allow user override

### Edge Case 1.2: Multi-Level Nested Directories

**Scenario**:
```
/Music/
  ├─ 1960s/
  │  └─ Rubber Soul/
  │     ├─ song1.mp3
  │     └─ song2.mp3
  └─ 1970s/
     └─ Abbey Road/
        ├─ song3.mp3
        └─ song4.mp3
```

**Current Behavior**: Groups by first-level subdirectory only ("1960s", "1970s")
**Expected**: Groups by album subdirectory ("Rubber Soul", "Abbey Road")

**Solution**: Detect deepest common level

```python
def find_album_level(directory: str, files: List[Dict]) -> int:
    """
    Find the directory level that represents albums.

    Strategy:
    1. For each file, count depth from base directory
    2. Find most common depth (likely album level)
    3. Group at that level
    """

    depths = []
    for file in files:
        rel_path = Path(file['path']).relative_to(directory)
        depth = len(rel_path.parts) - 1  # Subtract filename
        depths.append(depth)

    # Most common depth is likely album level
    most_common_depth = Counter(depths).most_common(1)[0][0]

    logger.info(f"Detected album level at depth {most_common_depth}")

    return most_common_depth

def group_files_by_album_level(directory: str, files: List[Dict], level: int) -> Dict:
    """Group files at specified directory depth."""

    album_groups = defaultdict(list)

    for file in files:
        rel_path = Path(file['path']).relative_to(directory)

        if len(rel_path.parts) - 1 >= level:
            album_key = '/'.join(rel_path.parts[:level])  # Use path at album level
        else:
            album_key = "[Root Files]"

        album_groups[album_key].append(file)

    return dict(album_groups)
```

**Trade-offs**:
- Pro: Works for multi-level structures
- Con: Heuristic may fail if directory structure inconsistent
- Decision: Use heuristic, fallback to first-level if confidence low

### Edge Case 1.3: 100+ Albums (Performance Limit)

**Scenario**: User loads directory with 150 album subdirectories

**Current Behavior**: Truncates at 100 albums, analyzes first 100 only

**Problem**: User doesn't know which albums were skipped

**Solution**: Smart truncation with user choice

```python
def analyze_per_album_context_smart(directory: str, files: List[Dict], max_albums: int = 100):
    """
    Analyze with smart truncation.

    If > max_albums:
    1. Sort albums by size (largest first) OR modification time (newest first)
    2. Analyze top N albums
    3. Return warning with truncation strategy
    """

    album_groups = group_files_by_subdirectory(directory, files)

    if len(album_groups) > max_albums:
        # Sort by file count (largest albums first)
        sorted_albums = sorted(
            album_groups.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )

        # Truncate
        truncated_albums = dict(sorted_albums[:max_albums])
        skipped_count = len(album_groups) - max_albums
        skipped_files = sum(len(files) for album, files in sorted_albums[max_albums:])

        warning = (
            f"Showing top {max_albums} largest albums (out of {len(album_groups)} total). "
            f"{skipped_count} smaller albums with {skipped_files} files were skipped. "
            f"To process all albums, load subdirectories individually."
        )

        return {
            "per_album_mode": True,
            "albums": analyze_albums(truncated_albums),
            "warning": warning,
            "truncated": True,
            "truncation_strategy": "largest_first"
        }
```

**UI Design**:
```
┌─────────────────────────────────────────────────────┐
│ ⚠️ Large Directory Detected                          │
├─────────────────────────────────────────────────────┤
│ Found 150 albums. Showing top 100 largest albums.   │
│                                                     │
│ Skipped: 50 smaller albums (2,345 files)            │
│                                                     │
│ Options:                                            │
│ ● Show largest 100 albums (recommended)             │
│ ○ Show newest 100 albums                           │
│ ○ Load subdirectories individually                  │
│                                                     │
│ [Apply] [Cancel]                                    │
└─────────────────────────────────────────────────────┘
```

**Trade-offs**:
- Pro: User aware of truncation, can choose strategy
- Con: Additional complexity
- Decision: Implement, default to "largest first"

---

## 2. Metadata Conflict Edge Cases

### Edge Case 2.1: Double Tempo Detection

**Scenario**: Detected BPM = 256, actual BPM = 128 (algorithm detected double-time)

**Current Behavior**: compare_bpm_values() checks if difference < 2%, may not catch double tempo

**Solution**: Detect common tempo ratios

```python
def compare_bpm_values_enhanced(bpm1, bpm2, tolerance=2.0):
    """
    Enhanced BPM comparison with ratio detection.

    Detects common issues:
    - Double tempo (2x)
    - Half tempo (0.5x)
    - Triple tempo (3x)
    """

    if not bpm1 or not bpm2:
        return False, None

    # Direct comparison
    diff_percent = abs((bpm1 - bpm2) / bpm1 * 100)
    if diff_percent <= tolerance:
        return True, "match"

    # Check for common ratios
    ratios = [2.0, 0.5, 3.0, 1.5, 0.33]
    for ratio in ratios:
        scaled_bpm2 = bpm2 * ratio
        scaled_diff = abs((bpm1 - scaled_bpm2) / bpm1 * 100)

        if scaled_diff <= tolerance:
            return True, f"possible {ratio}x tempo (detected {bpm2}, expected {bpm1})"

    return False, f"significant difference ({diff_percent:.1f}%)"
```

**Trade-offs**:
- Pro: Catches common detection errors
- Con: May flag valid differences
- Decision: Warn user, let them choose

### Edge Case 2.2: Enharmonic Key Equivalents

**Scenario**: C# vs Db (same pitch, different notation)

**Current Behavior**: compare_key_values() detects this

**Edge Case**: User prefers one notation over another

**Solution**: User preference for key notation

```python
def normalize_key_notation(key: str, user_preference: str = 'sharps') -> str:
    """
    Normalize key notation based on user preference.

    Options:
    - 'sharps': Prefer C#, F#, G#, etc.
    - 'flats': Prefer Db, Gb, Ab, etc.
    - 'auto': Choose based on key context (circle of fifths)
    """

    enharmonic_map = {
        'sharps': {
            'Db': 'C#', 'Eb': 'D#', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#',
            'Dbm': 'C#m', 'Ebm': 'D#m', 'Gbm': 'F#m', 'Abm': 'G#m', 'Bbm': 'A#m'
        },
        'flats': {
            'C#': 'Db', 'D#': 'Eb', 'F#': 'Gb', 'G#': 'Ab', 'A#': 'Bb',
            'C#m': 'Dbm', 'D#m': 'Ebm', 'F#m': 'Gbm', 'G#m': 'Abm', 'A#m': 'Bbm'
        }
    }

    if user_preference in enharmonic_map:
        return enharmonic_map[user_preference].get(key, key)

    return key
```

**Trade-offs**:
- Pro: Consistent notation across library
- Con: Additional setting
- Decision: Add preference, default to 'sharps' (most common in electronic music)

### Edge Case 2.3: MusicBrainz Rate Limiting

**Scenario**: User processes 50K files, hits MusicBrainz API rate limit (free tier: 1 req/sec)

**Current Behavior**: Fails silently or throws errors

**Solution**: Rate limiting with backoff

```python
from ratelimit import limits, sleep_and_retry

class MusicBrainzClient:
    def __init__(self):
        self.calls = 0
        self.start_time = time.time()

    @sleep_and_retry
    @limits(calls=1, period=1)  # 1 call per second
    def query(self, fingerprint: str):
        """Query MusicBrainz with rate limiting."""

        try:
            response = acoustid.lookup(fingerprint, self.api_key)
            self.calls += 1
            return response
        except RateLimitException:
            logger.warning("Rate limit hit, backing off...")
            time.sleep(5)  # Backoff 5 seconds
            return self.query(fingerprint)  # Retry
```

**UI Feedback**:
```
┌─────────────────────────────────────────────┐
│ ⚠️ MusicBrainz Rate Limit                    │
├─────────────────────────────────────────────┤
│ Querying MusicBrainz at 1 request/second    │
│ Estimated time: 13.8 hours for 50K files    │
│                                             │
│ Options:                                    │
│ ○ Continue (slow but complete)              │
│ ● Disable MusicBrainz for this operation    │
│ ○ Process in batches overnight               │
│                                             │
│ [Apply] [Cancel]                            │
└─────────────────────────────────────────────┘
```

**Trade-offs**:
- Pro: Prevents API bans, handles gracefully
- Con: Very slow for large libraries
- Decision: Warn user, offer alternatives

---

## 3. File System Edge Cases

### Edge Case 3.1: Very Long Filenames

**Scenario**: Generated filename > 255 characters (filesystem limit)

**Current Behavior**: safe_filename() truncates

**Problem**: Multiple files truncate to same name → collision

**Solution**: Smart truncation with uniqueness

```python
def safe_filename_with_length_limit(filename: str, max_length: int = 255, extension: str = '.mp3') -> str:
    """
    Truncate filename intelligently while maintaining uniqueness.

    Strategy:
    1. Remove extension temporarily
    2. If too long, truncate from middle (preserve start and end)
    3. Add hash suffix for uniqueness
    4. Re-add extension
    """

    stem = filename.replace(extension, '')

    if len(stem) + len(extension) <= max_length:
        return filename  # No truncation needed

    # Calculate available space
    available = max_length - len(extension) - 10  # Reserve 10 chars for hash

    if available <= 0:
        raise ValueError("Filename too short even after truncation")

    # Truncate from middle, preserve start and end
    start_length = available // 2
    end_length = available - start_length

    truncated = stem[:start_length] + "..." + stem[-end_length:]

    # Add hash for uniqueness
    file_hash = hashlib.md5(stem.encode()).hexdigest()[:8]
    truncated_with_hash = f"{truncated}_{file_hash}"

    return truncated_with_hash + extension
```

**Trade-offs**:
- Pro: Prevents collisions, maintains readability
- Con: Filenames less predictable
- Decision: Implement, log when truncation occurs

### Edge Case 3.2: Special Characters in Filenames

**Scenario**: Template generates filename with illegal characters (e.g., `/`, `\`, `:`)

**Current Behavior**: safe_filename() replaces with `_`

**Problem**: Loss of information

**Solution**: Smart replacement with preservation

```python
def safe_filename_preserve_meaning(filename: str) -> str:
    """
    Replace illegal characters while preserving meaning.

    Replacements:
    - / → ⧸ (division slash)
    - \ → ⧹ (set minus)
    - : → ꞉ (modifier letter colon)
    - | → ǀ (latin letter dental click)
    - ? → ？ (fullwidth question mark)
    - * → ⋆ (star operator)
    - < → ‹ (single left-pointing angle quotation mark)
    - > → › (single right-pointing angle quotation mark)
    - " → ″ (double prime)
    """

    replacements = {
        '/': '⧸', '\\': '⧹', ':': '꞉', '|': 'ǀ',
        '?': '？', '*': '⋆', '<': '‹', '>': '›', '"': '″'
    }

    safe = filename
    for illegal, replacement in replacements.items():
        safe = safe.replace(illegal, replacement)

    return safe
```

**Trade-offs**:
- Pro: Preserves meaning, visually similar
- Con: May not be compatible with all systems
- Decision: Add as opt-in setting, default to underscore replacement

### Edge Case 3.3: Case-Insensitive Filesystems

**Scenario**: macOS/Windows (case-insensitive), renaming "Song.mp3" → "song.mp3"

**Current Behavior**: os.replace() may fail or appear to do nothing

**Solution**: Two-step rename for case-only changes

```python
def rename_with_case_handling(src: Path, dst: Path) -> bool:
    """
    Handle case-only renames on case-insensitive filesystems.

    Strategy:
    1. Check if only case difference
    2. If yes, rename to temp name first, then to final name
    """

    if src.resolve() == dst.resolve():
        # Same file (already has desired name)
        return True

    if src.name.lower() == dst.name.lower():
        # Case-only change
        temp_name = dst.parent / f"_temp_{uuid.uuid4().hex[:8]}{dst.suffix}"

        # Step 1: Rename to temp
        os.rename(src, temp_name)

        # Step 2: Rename to final
        os.rename(temp_name, dst)

        return True
    else:
        # Normal rename
        os.rename(src, dst)
        return True
```

**Trade-offs**:
- Pro: Works on all filesystems
- Con: Two file system operations instead of one
- Decision: Implement, detect case-only changes automatically

---

## 4. Performance Edge Cases

### Edge Case 4.1: Network Timeout During MusicBrainz Lookup

**Scenario**: Network slow, MusicBrainz lookup times out

**Current Behavior**: Operation hangs or fails

**Solution**: Timeout with fallback

```python
import requests
from requests.exceptions import Timeout

def lookup_acoustid_with_timeout(file_path: Path, timeout: int = 10) -> Optional[Dict]:
    """
    Lookup with timeout and fallback.

    Args:
        file_path: File to analyze
        timeout: Timeout in seconds (default: 10)

    Returns:
        MusicBrainz data or None if timeout
    """

    try:
        response = requests.get(
            acoustid_url,
            params={'fingerprint': fingerprint},
            timeout=timeout
        )
        return response.json()
    except Timeout:
        logger.warning(f"MusicBrainz timeout for {file_path.name}, falling back to local analysis")
        return None
    except RequestException as e:
        logger.error(f"MusicBrainz error: {e}")
        return None
```

**Trade-offs**:
- Pro: Doesn't hang indefinitely
- Con: May miss MusicBrainz data
- Decision: Implement with configurable timeout

### Edge Case 4.2: Audio Analysis Hangs on Corrupted File

**Scenario**: Corrupted MP3 causes librosa to hang

**Current Behavior**: Entire operation stalls

**Solution**: Per-file timeout with thread termination

```python
from concurrent.futures import TimeoutError

def analyze_with_timeout(file_path: Path, timeout: int = 30) -> Dict:
    """
    Analyze audio with per-file timeout.

    Args:
        file_path: File to analyze
        timeout: Timeout in seconds (default: 30)

    Returns:
        Analysis results or error dict
    """

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(detect_bpm_and_key, file_path)

        try:
            result = future.result(timeout=timeout)
            return result
        except TimeoutError:
            logger.error(f"Audio analysis timeout for {file_path.name} (corrupted file?)")
            return {'bpm': None, 'key': None, 'error': 'timeout'}
```

**Trade-offs**:
- Pro: Prevents hangs
- Con: Skips problematic files
- Decision: Implement, log timeouts for user review

---

## 5. User Workflow Edge Cases

### Edge Case 5.1: User Cancels Mid-Operation

**Scenario**: User cancels rename operation after 5K/50K files processed

**Current Behavior**: Partial rename, no record of what was changed

**Solution**: Checkpoint-based cancellation with summary

```python
def cancel_with_summary(operation_id: str) -> Dict:
    """
    Cancel operation and generate summary.

    Returns summary:
    - Files renamed so far
    - Files remaining
    - Undo session created
    - Resume checkpoint saved
    """

    operation = get_operation(operation_id)

    # Set cancelled flag
    operation['cancelled'] = True

    # Generate summary
    summary = {
        'renamed_count': len(operation['renamed_files']),
        'remaining_count': operation['total'] - len(operation['renamed_files']),
        'undo_session_id': create_undo_session(operation['renamed_files']),
        'checkpoint_file': save_checkpoint(operation),
        'message': f"Cancelled after renaming {len(operation['renamed_files'])} of {operation['total']} files"
    }

    return summary
```

**UI Display**:
```
┌─────────────────────────────────────────────┐
│ ⏸ Operation Cancelled                        │
├─────────────────────────────────────────────┤
│ Successfully renamed: 5,234 files            │
│ Remaining: 44,766 files                      │
│                                             │
│ Options:                                    │
│ [Resume Later] [Undo All] [Close]           │
└─────────────────────────────────────────────┘
```

**Trade-offs**:
- Pro: User has clear options
- Con: Partial state requires careful handling
- Decision: Implement, save checkpoint on cancel

### Edge Case 5.2: Power Loss During Rename

**Scenario**: System crashes mid-rename

**Current Behavior**: Partial rename, no recovery

**Solution**: Atomic operations with recovery log

```python
def rename_with_recovery_log(src: Path, dst: Path, log_file: Path) -> bool:
    """
    Rename with recovery log for crash recovery.

    Log entry:
    {
        "timestamp": 1234567890,
        "src": "/path/to/original.mp3",
        "dst": "/path/to/renamed.mp3",
        "completed": false
    }

    After operation:
    {
        "completed": true
    }
    """

    # Log intent
    log_entry = {
        'timestamp': time.time(),
        'src': str(src),
        'dst': str(dst),
        'completed': False
    }
    append_to_log(log_file, log_entry)

    # Perform rename
    os.rename(src, dst)

    # Log completion
    log_entry['completed'] = True
    update_log(log_file, log_entry)

    return True
```

**Recovery on restart**:
```python
def recover_from_log(log_file: Path):
    """
    Recover from crash by checking log.

    For each incomplete operation:
    - Check if dst exists (rename completed despite log)
    - Check if src exists (rename not started)
    - Ask user what to do
    """

    incomplete = [entry for entry in read_log(log_file) if not entry['completed']]

    if incomplete:
        UI.showRecoveryDialog(incomplete)
```

**Trade-offs**:
- Pro: Can recover from crashes
- Con: Additional I/O overhead
- Decision: Implement for rename operations only (not preview)

---

## Implementation Priority

### P0 (Critical - Must Have)
1. Edge Case 1.1: Hybrid directory/metadata grouping
2. Edge Case 3.3: Case-insensitive filesystem handling
3. Edge Case 4.2: Audio analysis timeout

### P1 (High - Should Have)
4. Edge Case 1.3: Smart truncation for 100+ albums
5. Edge Case 2.3: MusicBrainz rate limiting
6. Edge Case 5.1: Cancel with summary

### P2 (Medium - Nice to Have)
7. Edge Case 1.2: Multi-level nested detection
8. Edge Case 2.1: Double tempo detection
9. Edge Case 3.1: Smart filename truncation
10. Edge Case 5.2: Power loss recovery

### P3 (Low - Future Enhancement)
11. Edge Case 2.2: Key notation preference
12. Edge Case 3.2: Special character preservation

---

## Testing Strategy

### Unit Tests
- Test hybrid grouping with various directory structures
- Test timeout mechanisms
- Test case-only rename
- Test truncation logic

### Integration Tests
- Test cancellation mid-operation
- Test recovery after crash (simulate with kill signal)
- Test MusicBrainz rate limit handling

### Performance Tests
- Benchmark grouping strategies (directory vs metadata vs hybrid)
- Measure timeout overhead
- Profile checkpoint save performance

---

## Status

✅ **Analysis Complete**
✅ **Solutions Proposed**
⏳ **Implementation**: Ready to start
📋 **Next Steps**: Implement P0 edge cases

**Estimated Implementation Time**: 2 weeks
**Testing Time**: 1 week
**Total**: 3 weeks to production

---

**Task #119 Status**: Complete
