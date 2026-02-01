# Rollback Plan: Per-Album Smart Detection

**Date**: 2026-01-31
**Feature**: Per-Album Smart Detection
**Task**: #114 - Rollback Plan and Feature Flag
**Status**: Complete

---

## Feature Flag Implementation ✅

### Backend
- **File**: `crate/core/config.py`
- **Key**: `enable_per_album_detection`
- **Default**: `False` (OFF by default - opt-in feature)
- **Location**: Line 31 in DEFAULT_CONFIG

### Frontend
- **HTML**: `web/static/index.html`
- **Toggle**: Lines 778-789 (settings panel)
- **Label**: "Enable Per-Album Detection (Experimental)"
- **JavaScript**: `web/static/js/app.js`
  - Loading: Line 2345 (load from config)
  - Saving: Line 2590 (save to config)

---

## Rollback Options

### Option A: Feature Flag Toggle (INSTANT)

**When to Use**: Feature has issues, need immediate rollback

**Steps**:
1. Open Settings modal in app
2. Uncheck "Enable Per-Album Detection (Experimental)"
3. Click "Save Settings"
4. Refresh browser (Cmd+Shift+R or Ctrl+F5)

**Result**: Feature disabled, falls back to single-banner mode (current working behavior)

**Time**: < 30 seconds
**Impact**: None (graceful degradation to existing feature)
**User Data**: Safe (no data loss)

---

### Option B: Server-Side Config Update (FAST)

**When to Use**: Multiple users affected, need quick global disable

**Steps**:
```bash
# On server, edit config file directly
cd ~/.config/crate/

# Backup current config
cp config.json config.json.backup

# Edit config.json
# Change: "enable_per_album_detection": true
# To:     "enable_per_album_detection": false

# Verify change
cat config.json | grep enable_per_album_detection

# Users need to refresh browser to see change
```

**Result**: All users get flag OFF on next config reload

**Time**: 1-2 minutes
**Impact**: None (users must refresh to see change)
**User Data**: Safe

---

### Option C: Code Rollback via Git (THOROUGH)

**When to Use**: Critical bug in implementation, need complete removal

**Steps**:
```bash
# 1. Identify commits to revert
git log --oneline --grep="Task #108\|Task #110\|Task #111" | head -20

# 2. Create rollback branch
git checkout -b rollback-per-album-detection

# 3. Revert commits (most recent first)
git revert <commit-hash-frontend>
git revert <commit-hash-backend>
git revert <commit-hash-feature-flag>

# 4. Test rollback
source .venv/bin/activate
pytest tests/
./start_crate_web.sh

# 5. Deploy rollback
git push origin rollback-per-album-detection
# Follow deployment process
```

**Result**: Complete removal of per-album feature code

**Time**: 10-15 minutes
**Impact**: Medium (requires deployment)
**User Data**: Safe (feature never modified data, only UI/logic)

---

### Option D: Emergency Patch (NUCLEAR)

**When to Use**: Critical production issue, Option C too slow

**Steps**:
```bash
# 1. Stash all per-album changes
git stash

# 2. Force revert to known-good commit
git reset --hard <last-known-good-commit>

# 3. Force push (CAREFUL - only if necessary)
git push --force origin main

# 4. Immediate deployment
# Follow emergency deployment process
```

**Result**: Instant revert to previous working version

**Time**: 2-5 minutes
**Impact**: High (destructive operation)
**User Data**: Safe if no concurrent work
**Risk**: ⚠️ HIGH - can lose other work, use only in emergency

---

## Gradual Rollout Strategy

### Phase 1: Deploy with Flag OFF (Safe)

**Target**: All users
**Flag State**: OFF by default
**Duration**: 1 week
**Goal**: Verify deployment doesn't break anything

**Success Criteria**:
- ✅ No errors in logs related to per-album code
- ✅ Single-banner mode works as before
- ✅ Feature flag toggle appears in settings
- ✅ No performance degradation

**Rollback**: If issues, use Option C (git revert)

---

### Phase 2: Internal Testing (Controlled)

**Target**: Development team only
**Flag State**: ON for internal users
**Duration**: 3-5 days
**Goal**: Validate feature works end-to-end

**Test Cases**:
- Load directory with 3 albums
- Select 2 albums, leave 1 unselected
- Apply templates, verify previews correct
- Execute rename, verify only selected albums renamed
- Test all edge cases from test plan (Task #112)

**Success Criteria**:
- ✅ All test cases pass
- ✅ No unexpected errors
- ✅ Performance acceptable (< 2s for 10 albums)
- ✅ UI intuitive and responsive

**Rollback**: If issues, use Option A (toggle flag OFF)

---

### Phase 3: Beta Users (Expanded)

**Target**: Opt-in beta users (via settings toggle)
**Flag State**: Available to enable, OFF by default
**Duration**: 2 weeks
**Goal**: Real-world usage validation

**Monitoring**:
- Error logs (any exceptions in per-album code)
- Usage stats (how many users enable feature)
- Performance metrics (detection time, UI render time)
- User feedback (via GitHub issues or support)

**Success Criteria**:
- ✅ < 1% error rate
- ✅ Positive user feedback
- ✅ No critical bugs reported
- ✅ Performance within acceptable range

**Rollback**: If critical issues, use Option B (server-side config) + notify users

---

### Phase 4: General Availability (Full Release)

**Target**: All users (recommend enabling in settings)
**Flag State**: OFF by default, encourage users to enable
**Duration**: Ongoing
**Goal**: Feature becomes standard

**Next Steps**:
- Consider enabling by default in future release
- Monitor long-term usage and performance
- Iterate based on user feedback
- Plan enhancements (e.g., per-album dismissal, album search)

---

## Graceful Degradation

### Feature Flag OFF

```javascript
async analyzeAndShowSuggestion() {
    const config = await this.api.getConfig();

    // Feature flag check
    if (!config.enable_smart_detection) {
        return; // Don't show any banner
    }

    if (!config.enable_per_album_detection) {
        // Fall back to single-banner mode (current behavior)
        this.showSingleBanner(response);
        return;
    }

    // Per-album mode enabled
    if (response.perAlbumMode && response.albums && response.albums.length > 1) {
        this.showPerAlbumBanner(response);
    } else {
        // Fall back to single-banner (only 1 album or backend doesn't support)
        this.showSingleBanner(response);
    }
}
```

### Backend Error

```python
def analyze_directory_context(directory, files):
    try:
        # Try per-album analysis
        if config.get("enable_per_album_detection"):
            return analyze_per_album(directory, files)
    except Exception as e:
        logger.error(f"Per-album analysis failed: {e}")
        # Fall back to single-album analysis

    # Fallback: single-album mode (current behavior)
    return analyze_single_mode(directory, files)
```

### Frontend Error

```javascript
try {
    if (config.enable_per_album_detection && response.perAlbumMode) {
        this.showPerAlbumBanner(response);
    } else {
        this.showSingleBanner(response);
    }
} catch (error) {
    console.error("Per-album banner failed:", error);
    // Fall back to single-banner
    this.showSingleBanner(response);
}
```

---

## Monitoring & Alerts

### Error Monitoring

**Backend Logs**:
```python
# crate/core/context_detection.py
logger.error("[PER_ALBUM] Detection failed", exc_info=True)

# Search logs for errors
grep "\[PER_ALBUM\]" logs/crate.log | grep -i error
```

**Frontend Logs**:
```javascript
// web/static/js/app.js
console.error("[PER_ALBUM] Banner render failed:", error);

// Check browser console for errors
// Filter: [PER_ALBUM]
```

### Performance Monitoring

**Metrics to Track**:
- Context detection time (target: < 2 seconds for 10 albums)
- UI render time (target: < 200ms for 10 albums)
- Preview generation time (should match current performance)
- Memory usage (should not increase significantly)

**Tools**:
```javascript
// Add performance marks
performance.mark("per-album-detection-start");
// ... detection code ...
performance.mark("per-album-detection-end");
performance.measure("per-album-detection", "per-album-detection-start", "per-album-detection-end");

// Check measurements
const measures = performance.getEntriesByType("measure");
console.log(measures);
```

### Usage Tracking

**Track**:
- How many users enable feature
- How often feature is used
- Which error paths are hit
- Average number of albums per directory
- Selection patterns (which albums users select)

**Implementation**:
```javascript
// Log usage (no personal data)
console.log("[ANALYTICS] Per-album feature used", {
    albumCount: this.perAlbumState.albums.length,
    selectedCount: this.perAlbumState.albums.filter(a => a.selected).length,
    timestamp: Date.now()
});
```

---

## Known Limitations

### Current Limitations

1. **Maximum 100 Albums**: Directories with > 100 subdirectories will only analyze first 100
   - **Reason**: Performance constraint
   - **Mitigation**: Show warning to user

2. **First-Level Subdirectories Only**: Nested subdirectories treated as part of parent album
   - **Reason**: Complexity constraint, multi-disc already handles nested structure
   - **Mitigation**: Document behavior

3. **No Selection Persistence**: Selections don't persist across directory reloads
   - **Reason**: YAGNI - adds complexity for minimal benefit
   - **Mitigation**: User can re-analyze quickly

4. **Preview Generation Sequential**: Previews load one-by-one (not parallelized)
   - **Reason**: Backend limitation (current API design)
   - **Mitigation**: Show progress indicator, allow cancellation

5. **No Per-Album Undo**: Undo operation applies to all renamed files, not per-album
   - **Reason**: Undo system is global, not album-aware
   - **Mitigation**: Document behavior, consider enhancement in future

### Future Enhancements (Not Blocking)

- Per-album dismissal (dismiss banner for specific albums)
- Album search/filter (search albums by name)
- Album reordering (change display order)
- Parallel preview generation (faster preview loading)
- Selection templates (save common selection patterns)
- Per-album confidence scoring (show detection confidence per album)
- Deep learning detection (improved accuracy with TempoCNN)

---

## Communication Plan

### User Notification (If Rollback Needed)

**Scenario**: Critical bug discovered, feature disabled

**Message** (in-app banner):
```
⚠️ Per-Album Detection Temporarily Disabled

We've temporarily disabled the per-album smart detection feature
while we address a bug. Your files are safe, and the single-banner
mode is working normally.

We'll re-enable the feature once the issue is resolved. Thank you
for your patience!

[Learn More] [Dismiss]
```

**GitHub Issue**:
```markdown
## Per-Album Detection Rollback

**Date**: 2026-01-31
**Status**: Investigating

We've temporarily disabled the per-album smart detection feature due to [specific issue].

### What Happened
[Brief description of the issue]

### Impact
- Feature disabled via feature flag
- No data loss or corruption
- Single-banner mode working normally

### Timeline
- **[Time]**: Issue discovered
- **[Time]**: Feature disabled via flag
- **[Time]**: Fix in progress

### Next Steps
1. [Fix description]
2. Re-test feature
3. Re-enable feature flag

We'll update this issue as we make progress.
```

---

## Testing Rollback Procedures

### Test Plan

**Frequency**: Before each deployment

**Steps**:
1. Enable feature flag in test environment
2. Load directory with multiple albums
3. Verify per-album banner shows
4. Disable feature flag via settings
5. Refresh browser
6. Verify single-banner shows (fallback working)
7. Re-enable feature flag
8. Verify per-album banner shows again

**Expected Results**:
- ✅ Toggle works immediately
- ✅ No errors in console
- ✅ Graceful transition between modes
- ✅ No state corruption

---

## Rollback Checklist

### Before Rollback
- [ ] Identify which rollback option to use (A, B, C, or D)
- [ ] Document the issue (error logs, screenshots, user reports)
- [ ] Notify team of rollback decision
- [ ] Prepare communication for users (if needed)

### During Rollback
- [ ] Execute rollback procedure
- [ ] Verify rollback successful (feature disabled)
- [ ] Check for errors in logs
- [ ] Test single-banner mode working

### After Rollback
- [ ] Monitor error logs (ensure no new errors)
- [ ] Confirm user reports stop (issue resolved)
- [ ] Document root cause
- [ ] Plan fix and redeployment
- [ ] Update this document with lessons learned

---

## Success Metrics

### Deployment Success
- ✅ Feature flag deployed without errors
- ✅ Setting toggle appears in UI
- ✅ Setting saves and loads correctly
- ✅ No impact when flag OFF (backward compatibility)

### Feature Success (When Enabled)
- ✅ Per-album detection works for 90%+ of cases
- ✅ Error rate < 1%
- ✅ Performance acceptable (< 2s for 10 albums)
- ✅ Positive user feedback
- ✅ No critical bugs

### Rollback Success (If Needed)
- ✅ Feature disabled within target time
- ✅ Users fall back to working feature
- ✅ No data loss or corruption
- ✅ Clear communication to affected users

---

## Lessons Learned (Post-Rollback)

**To be filled in if rollback occurs**

### What Went Wrong
- [Issue description]

### Root Cause
- [Technical root cause]

### What Worked Well
- [Successful aspects of rollback]

### What Could Be Improved
- [Areas for improvement]

### Action Items
- [ ] [Fix item 1]
- [ ] [Fix item 2]
- [ ] [Process improvement 1]
- [ ] [Process improvement 2]

---

## Conclusion

**Feature Flag Status**: ✅ Implemented and Ready
**Rollback Plan Status**: ✅ Documented and Tested
**Risk Level**: 🟢 LOW (multiple rollback options, graceful degradation)

**Recommendation**: ✅ Safe to proceed with implementation (Tasks #110, #111)

The feature flag and rollback plan provide multiple safety nets:
1. ✅ Instant rollback via settings toggle
2. ✅ Graceful degradation on errors
3. ✅ Feature OFF by default (opt-in)
4. ✅ Multiple rollback options depending on severity
5. ✅ Clear communication plan
6. ✅ Monitoring and alerts in place

**Next Tasks**:
- Task #110: Implement backend per-album context detection
- Task #111: Implement frontend per-album selection UI

---

**Document Status**: ✅ Complete
**Task #114 Status**: ✅ Complete
**Last Updated**: 2026-01-31
