# User Guide: Per-Album Smart Detection

**Feature**: Per-Album Smart Detection
**Status**: Experimental (opt-in)
**Version**: 20260131-21

---

## What Is Per-Album Detection?

When you load a directory containing multiple album subdirectories, Crate can now analyze each album separately and let you choose which albums should use smart track detection templates.

**Before**: One template suggestion for ALL albums (take it or leave it)
**Now**: Individual control per album (select which albums need smart templates)

---

## How to Enable

1. Open Settings (⚙️ gear icon)
2. Enable "Smart Track Detection (Beta)"
3. Enable "Per-Album Detection (Experimental)"
4. Save Settings

---

## How to Use

### Step 1: Load Multi-Album Directory

Load a directory containing multiple album subdirectories:
```
/Music/New_Acquisitions/
    Album_A/
    Album_B/
    Album_C/
```

### Step 2: Review Album List

A banner appears showing detected albums:
- ✓ ALBUM = High confidence, recommended for smart template
- ~ PARTIAL_ALBUM = Medium confidence, review carefully
- ✗ SINGLES = Not recommended (no track sequence)

### Step 3: Select Albums

- **Auto-selected**: Albums with high-confidence ALBUM detection
- **Manual selection**: Check/uncheck boxes for each album
- **Quick actions**:
  - Select All: Check all albums
  - Deselect All: Uncheck all albums
  - Invert Selection: Flip all selections

### Step 4: Apply Templates

Click "Apply to Selected" button:
- Selected albums → Use smart template (e.g., `{track} - {title}`)
- Unselected albums → Use your global template from settings

### Step 5: Review and Rename

- Check preview column
- Select files to rename
- Click Rename

---

## Example Use Case

**Scenario**: DJ loads `/Music/Inbox/` with 10 new albums

**Albums Detected**:
- Greatest Hits Vol 1 ✓ ALBUM (12 tracks, 1-12) → ✅ Auto-selected
- Live Recordings ~ PARTIAL_ALBUM (gaps in tracks) → ⬜ Not selected
- Top 40 Compilation ✗ SINGLES (no sequence) → ⬜ Not selected
- Best Of Album ✓ ALBUM (15 tracks, 1-15) → ✅ Auto-selected

**Action**:
DJ reviews, agrees with auto-selections, clicks "Apply to Selected"

**Result**:
- Greatest Hits & Best Of renamed with smart template
- Live Recordings & Top 40 renamed with global template
- All done in one batch operation!

---

## Tips & Tricks

### Expand Album Details

Click ▶ button to see:
- Full album path
- Detection reason
- Suggested template
- File count

### Quick Workflow

1. Load directory → banner shows
2. Review auto-selections (usually correct)
3. Adjust if needed
4. Apply → Done!

**Target**: < 5 clicks from load to rename

### When to Use

**Use per-album detection when**:
- Loading mixed directories (albums + compilations + singles)
- Processing multiple albums at once
- Different albums need different templates

**Don't use when**:
- Single album directory (use regular smart detection)
- All albums are similar (use Select All)
- Prefer manual control (disable feature)

---

## Troubleshooting

### Banner Doesn't Show

**Check**:
- Feature enabled in settings?
- Multiple albums in directory?
- At least 2 subdirectories?

**Solution**: Enable in settings, load multi-album directory

### Wrong Detection Type

**Example**: Album marked as SINGLES but has track numbers

**Solution**:
- Uncheck the album
- Use global template from settings
- Or manually edit template

### Performance Slow

**Scenario**: 100+ albums, slow loading

**Solution**: System limits to 100 albums (performance)
- Warning shown if exceeded
- Load smaller subdirectories

### Previews Wrong Template

**Check**:
- Did you click "Apply to Selected"?
- Are correct albums checked?
- Is feature flag enabled?

**Solution**: Reselect albums, click Apply again

---

## Technical Details

### Detection Algorithm

**Per Album**:
1. Group files by subdirectory
2. Extract track numbers from metadata
3. Check if sequential (1, 2, 3...)
4. Classify: ALBUM, PARTIAL, INCOMPLETE, or SINGLES
5. Suggest template based on classification

### Performance Limits

- Maximum 100 albums analyzed
- Warning shown if exceeded
- First-level subdirectories only

### Feature Flag

- OFF by default (opt-in)
- Can be disabled anytime in settings
- Falls back to single-banner mode when OFF

---

## Keyboard Shortcuts

- **Tab**: Navigate between albums
- **Space**: Toggle album checkbox (when focused)
- **Enter**: Apply to selected (when button focused)
- **Escape**: Dismiss banner

---

## FAQ

**Q: Do I need an API key?**
A: No. Per-album detection runs locally on your machine.

**Q: Will this work with 1000 albums?**
A: Limited to 100 albums for performance. Split into smaller directories.

**Q: Can I save album selections?**
A: No. Selections don't persist. Re-analyze each time you load directory.

**Q: What if detection is wrong?**
A: Uncheck the album, it will use your global template instead.

**Q: How is this different from regular smart detection?**
A: Regular shows one suggestion for all files. Per-album lets you choose per album.

---

## Known Limitations

1. **100-album limit**: Performance constraint
2. **No selection persistence**: Re-analyze each load
3. **First-level subdirs only**: Nested dirs treated as parent album
4. **Sequential preview loading**: Not parallel (future enhancement)

---

## Feedback

Found a bug or have suggestions?
- GitHub Issues: [github.com/yourusername/crate/issues]
- Feature flag can be disabled anytime if issues occur

---

## Related Features

- **Smart Track Detection**: Single-banner mode (predecessor)
- **Remember Last Directory**: Auto-restore path on startup
- **Metadata Columns**: View album, year, genre, duration

---

**Status**: ✅ User Guide Complete
**Version**: 1.0
**Last Updated**: 2026-01-31
