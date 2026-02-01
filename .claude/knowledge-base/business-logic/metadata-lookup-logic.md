# Metadata Lookup Business Logic

## Overview

The DJ MP3 Renamer uses a **three-tier metadata strategy** to ensure files are renamed with accurate information:

1. **ID3 Tags (Primary Source)** - Embedded metadata in MP3 files
2. **AcoustID/MusicBrainz (Optional Enhancement)** - Audio fingerprinting database lookup
3. **AI Audio Analysis (Fallback)** - Local BPM/Key detection using librosa

## Decision Flow Diagram

```
┌─────────────────────────────────────┐
│  User loads MP3 files into Web UI  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Backend reads ID3 tags (ALWAYS)    │
│  File: dj_mp3_renamer/core/io.py    │
│  Function: read_mp3_metadata()      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Metadata extracted:                │
│  - artist, title, album             │
│  - bpm, key (if present in tags)    │
│  - year, label, track               │
│  - mix info (inferred from title)   │
└──────────────┬──────────────────────┘
               │
               ▼
        ┌──────┴──────┐
        │             │
        ▼             ▼
   [PREVIEW]     [ENHANCE METADATA?]
   Mode          (auto_detect=True)
        │             │
        │             ▼
        │      ┌─────────────────────────┐
        │      │ Check config settings:  │
        │      │ - enable_musicbrainz    │
        │      │ - acoustid_api_key      │
        │      │ - verify_mode           │
        │      └─────────┬───────────────┘
        │                │
        │                ▼
        │         ┌──────┴──────┐
        │         │             │
        │         ▼             ▼
        │    [MB ENABLED]  [MB DISABLED]
        │         │             │
        │         ▼             │
        │  ┌──────────────┐    │
        │  │ AcoustID     │    │
        │  │ Fingerprint  │    │
        │  │ + Lookup     │    │
        │  └──────┬───────┘    │
        │         │             │
        │         ▼             ▼
        │    [MB Data?]   [AI Analysis]
        │         │             │
        │    Yes  │  No         │
        │    ┌────┴────┐        │
        │    ▼         ▼        │
        │  [Use MB] [AI Analysis]
        │    │         │        │
        │    └────┬────┴────────┘
        │         │
        │         ▼
        │  ┌──────────────────┐
        │  │ Conflict         │
        │  │ Resolution       │
        │  │ (if multiple     │
        │  │  sources differ) │
        │  └──────┬───────────┘
        │         │
        │         ▼
        │  ┌──────────────────┐
        │  │ Write enhanced   │
        │  │ data back to     │
        │  │ ID3 tags         │
        │  └──────┬───────────┘
        │         │
        └─────────┴──────────┐
                  │
                  ▼
          ┌──────────────┐
          │ Build        │
          │ filename     │
          │ from         │
          │ template     │
          └──────┬───────┘
                  │
                  ▼
          ┌──────────────┐
          │ Show preview │
          │ or execute   │
          │ rename       │
          └──────────────┘
```

## When ID3 Tags Are Used

**ALWAYS** - ID3 tags are the primary metadata source.

### Code Reference
- **File**: `dj_mp3_renamer/core/io.py`
- **Function**: `read_mp3_metadata(file_path: Path, logger: Logger)`
- **Lines**: ~150-200 (estimates based on file structure)

### Process
1. Opens MP3 file using `mutagen` library
2. Reads ID3v2 tags (industry standard)
3. Extracts fields:
   - `TPE1` → artist
   - `TIT2` → title
   - `TALB` → album
   - `TDRC` → year
   - `TPUB` → label
   - `TRCK` → track number
   - `TBPM` → BPM
   - `TKEY` → musical key

4. **Always returns metadata** - even if empty strings
5. **Never fails** - returns error message if file unreadable

### Usage in Web UI
- **Endpoint**: `POST /api/directory/list`
- **File**: `web/main.py:182-247`
- When user selects directory, backend scans for MP3 files
- Metadata loaded on-demand (lazy loading for performance)

### Usage in Preview
- **Endpoint**: `POST /api/rename/preview`
- **File**: `web/main.py:296-339`
- **API Method**: `RenamerAPI.preview_rename()`
- **File**: `dj_mp3_renamer/api/renamer.py:670-756`
- Reads ID3 tags for ALL files in preview
- **Fast operation** - no audio analysis or database lookups
- Uses `auto_detect=False` to skip expensive operations

## When AcoustID API Is Used

**CONDITIONALLY** - Only when:
1. User has configured AcoustID API key (optional)
2. Config setting `enable_musicbrainz` is `True`
3. Request has `auto_detect=True` (e.g., user clicks "Enhance Metadata" button)
4. Metadata is missing OR `verify_mode=True`

### Code Reference
- **File**: `dj_mp3_renamer/core/audio_analysis.py`
- **Function**: `lookup_acoustid(file_path, logger, api_key)`
- **Lines**: `171-248`

### Process
1. Generates audio fingerprint using `acoustid.match()`
2. Sends fingerprint to AcoustID API (requires internet)
3. API queries MusicBrainz database (~40 million tracks)
4. Returns matches with confidence scores (0.0-1.0)
5. Selects best match if confidence > 0.5

### What AcoustID Returns
From code analysis (audio_analysis.py:226-236):
```python
best_match = {
    "artist": artist,          # Usually available
    "title": title,            # Usually available
    "recording_id": recording_id,  # MusicBrainz ID
    "confidence": score,       # 0.5-1.0
    "album": None,             # Would need additional MB API call
    "year": None,              # Would need additional MB API call
    "bpm": None,               # Rarely available in free tier
    "key": None,               # Rarely available in free tier
}
```

**Important**: Free-tier AcoustID lookups **rarely include BPM/Key**. These fields are mostly empty, which is why AI audio analysis is the fallback.

### Configuration Settings
- **Config file**: `~/.config/dj-mp3-renamer/config.json`
- **Settings**:
  - `acoustid_api_key`: API key (default: "8XaBELgH" - public key)
  - `enable_musicbrainz`: Enable/disable lookups (default: `false`)
  - `verify_mode`: Always lookup even if tags exist (default: `false`)
  - `use_mb_for_all_fields`: Use MB for artist/title too (default: `true`)

### Usage Flow
1. User opens Settings dialog and enters AcoustID API key
2. User enables "Enhanced Metadata" checkbox
3. Web UI sends request with `enhance_metadata: true`
4. Backend calls `_enhance_metadata()` method
5. Method calls `lookup_acoustid()` if enabled

### Code Path
```
Web UI: app.js (user clicks "Enhance Metadata")
    ↓
Backend: web/main.py:296-339 (POST /api/rename/preview)
    ↓
API: renamer.py:235-386 (_enhance_metadata)
    ↓
Core: audio_analysis.py:171-248 (lookup_acoustid)
    ↓
External: acoustid.match() → AcoustID API → MusicBrainz DB
```

## When AI Audio Analysis Is Used

**CONDITIONALLY** - Only when:
1. Request has `auto_detect=True` (same trigger as AcoustID)
2. Metadata field is missing (empty BPM or Key)
3. AcoustID lookup failed OR didn't return BPM/Key
4. OR `verify_mode=True` (always analyze for verification)

### Code Reference
- **File**: `dj_mp3_renamer/core/audio_analysis.py`
- **Functions**:
  - `detect_bpm_from_audio()` - Lines 31-92
  - `detect_key_from_audio()` - Lines 95-168
  - `auto_detect_metadata()` - Lines 251-337 (orchestrates both)

### BPM Detection Process
1. Loads first 60 seconds of audio using `librosa.load()`
2. Resamples to 22050 Hz (performance optimization)
3. Runs beat tracking algorithm: `librosa.beat.beat_track()`
4. Extracts tempo in BPM
5. Validates range (60-200 BPM for typical DJ music)
6. Returns BPM as string or `None` if failed

**Performance**: ~3-5 seconds per file

### Key Detection Process
1. Loads first 30 seconds of audio using `librosa.load()`
2. Computes chromagram: `librosa.feature.chroma_cqt()`
3. Analyzes pitch class distribution
4. Compares major vs minor triad strengths
5. Returns key as "C maj", "A min", etc.

**Accuracy Note**: Key detection is less reliable than BPM (per code comments)

**Performance**: ~2-4 seconds per file

### Fallback Priority
The `auto_detect_metadata()` function implements smart fallback:

```python
# Priority order (audio_analysis.py:287-337):
1. Use existing ID3 tag values (if present)
   ↓ (if missing or force_analysis=True)
2. Try AcoustID/MusicBrainz lookup (if enabled)
   ↓ (if MB didn't return BPM/Key)
3. Run AI audio analysis (librosa)
   ↓
4. Return best available value
```

### Code Path for AI Analysis
```
API: renamer.py:235-386 (_enhance_metadata)
    ↓
Core: audio_analysis.py:251-337 (auto_detect_metadata)
    ↓
    ├─ audio_analysis.py:171-248 (lookup_acoustid) [if enabled]
    │  ↓ [if MB didn't return BPM/Key]
    ├─ audio_analysis.py:31-92 (detect_bpm_from_audio)
    └─ audio_analysis.py:95-168 (detect_key_from_audio)
```

## Conflict Resolution

When multiple sources provide different values for the same field, the system uses conflict resolution logic.

### Code Reference
- **File**: `dj_mp3_renamer/core/conflict_resolution.py` (imported in renamer.py:18)
- **Function**: `resolve_metadata_conflict()`
- **Usage**: `renamer.py:294-356`

### Resolution Strategy
For each field (artist, title, BPM, key):

1. **Collect all sources**:
   - ID3 tag value
   - MusicBrainz value (if available)
   - AI analysis value (if available)
   - MusicBrainz confidence score

2. **Apply rules**:
   - If `verify_mode=True`: Log all conflicts, user must review
   - If MusicBrainz confidence > threshold: Prefer MB over tags
   - If MB doesn't have value: Use AI analysis
   - If neither MB nor AI: Keep ID3 tag value

3. **Track source**: Each field gets a `*_source` attribute:
   - `bpm_source`: "Tags" | "MusicBrainz" | "AI Audio" | "Failed"
   - `key_source`: "Tags" | "MusicBrainz" | "AI Audio" | "Failed"

4. **Write back to tags**: If enhanced data is used, write back to ID3 tags
   - **File**: `dj_mp3_renamer/core/io.py`
   - **Function**: `write_bpm_key_to_tags()`
   - **Reference**: `renamer.py:376-380`

### Example Conflict
```
ID3 Tag BPM: "125"
MusicBrainz BPM: "128" (confidence: 0.85)
AI Analysis BPM: "127"

Result: Uses MusicBrainz "128" (high confidence)
Final metadata: {"bpm": "128", "bpm_source": "MusicBrainz"}
Writes "128" back to ID3 tag for future consistency
```

## Web UI Integration

### Preview Mode (Default)
- **Endpoint**: `POST /api/rename/preview`
- **Parameters**: `enhance_metadata: false` (default)
- **Behavior**:
  - Reads ID3 tags only
  - Fast (milliseconds per file)
  - No external API calls
  - No audio analysis
  - Shows preview of filename changes

### Enhanced Mode (User Opt-In)
- **Endpoint**: `POST /api/rename/preview`
- **Parameters**: `enhance_metadata: true`
- **Trigger**: User clicks "Enhance Metadata" button (not yet implemented in UI)
- **Behavior**:
  - Reads ID3 tags
  - Runs AcoustID lookup (if configured)
  - Runs AI audio analysis (if needed)
  - Resolves conflicts
  - Writes enhanced data back to tags
  - Shows preview with enhanced metadata
  - **Slow**: ~5-10 seconds per file

### Execute Mode
- **Endpoint**: `POST /api/rename/execute`
- **Parameters**: `file_paths: [...]`, `template: "..."`
- **Behavior**:
  - Uses metadata from preview (cached)
  - Does NOT re-analyze (performance optimization)
  - Executes actual file renames
  - Returns operation ID for progress tracking

## Performance Implications

### Fast Path (ID3 Only)
- **Time**: <10ms per file
- **Bottleneck**: Disk I/O
- **Scalability**: Can handle 10,000+ files easily

### Slow Path (Enhanced Metadata)
- **Time**: 5-10 seconds per file
- **Bottleneck**: Audio analysis (CPU-bound)
- **Scalability**:
  - 100 files = ~10-15 minutes
  - 1,000 files = ~1.5-3 hours
  - 10,000 files = ~15-30 hours

### Recommendation
From capacity analysis (README.md):
- **Web UI**: Best for 1-10K files (ID3 only)
- **CLI**: Required for 50K+ files
- **Enhanced metadata**: Use selectively on important tracks only

## Summary Table

| Metadata Source | When Used | Speed | Accuracy | Requirements |
|----------------|-----------|-------|----------|--------------|
| **ID3 Tags** | Always (primary) | Fast (10ms) | Depends on file | None |
| **AcoustID/MB** | Optional (if configured + auto_detect=True) | Medium (1-2s) | High (if found) | API key + internet |
| **AI Audio Analysis** | Fallback (if MB fails + auto_detect=True) | Slow (5-10s) | Good (BPM), Fair (Key) | librosa + CPU |

## Code References Summary

| Component | File | Key Functions |
|-----------|------|---------------|
| ID3 Tag Reading | `dj_mp3_renamer/core/io.py` | `read_mp3_metadata()` |
| AcoustID Lookup | `dj_mp3_renamer/core/audio_analysis.py:171-248` | `lookup_acoustid()` |
| BPM Detection | `dj_mp3_renamer/core/audio_analysis.py:31-92` | `detect_bpm_from_audio()` |
| Key Detection | `dj_mp3_renamer/core/audio_analysis.py:95-168` | `detect_key_from_audio()` |
| Orchestration | `dj_mp3_renamer/core/audio_analysis.py:251-337` | `auto_detect_metadata()` |
| Conflict Resolution | `dj_mp3_renamer/core/conflict_resolution.py` | `resolve_metadata_conflict()` |
| Enhancement Logic | `dj_mp3_renamer/api/renamer.py:235-386` | `_enhance_metadata()` |
| Web API Preview | `web/main.py:296-339` | `preview_rename()` |
| Web API Execute | `web/main.py:343-378` | `execute_rename()` |

## Configuration File Example

Location: `~/.config/dj-mp3-renamer/config.json`

```json
{
  "acoustid_api_key": "8XaBELgH",
  "enable_musicbrainz": false,
  "verify_mode": false,
  "use_mb_for_all_fields": true,
  "auto_detect_bpm": true,
  "auto_detect_key": true,
  "default_template": "{artist} - {title}{mix_paren}{kb}",
  "first_run_complete": true
}
```

## User Experience Implications

### Current Web UI (Screenshot Analysis)
From the provided screenshot:
- Table shows: FILENAME, ARTIST, TITLE, BPM, KEY, SOURCE, ACTIONS
- **SOURCE column** shows "ID3" badge → indicates metadata came from ID3 tags
- No visible "Enhance Metadata" button → users cannot trigger AcoustID/AI analysis from UI
- All metadata displayed is from ID3 tags only (fast path)

### Recommended UX Improvements
1. **Add "Enhance Metadata" toggle** per file or globally
2. **Show metadata source** with color coding:
   - 🏷️ Blue = ID3 Tags
   - 🎵 Green = MusicBrainz (high confidence)
   - ⚡ Yellow = AI Analysis
3. **Progress indicator** for enhanced mode (5-10s per file)
4. **Conflict warnings** when sources disagree (verify_mode)
