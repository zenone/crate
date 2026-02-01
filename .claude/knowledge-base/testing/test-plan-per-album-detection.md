# Test Plan: Per-Album Smart Detection

**Date**: 2026-01-31
**Feature**: Per-Album Smart Detection (Tasks #108-#111)
**Status**: Ready for Testing

---

## Test Prerequisites

1. Feature flag enabled: Settings → Enable Per-Album Detection (Experimental) ✓
2. Smart Track Detection enabled: Settings → Enable Smart Track Detection ✓
3. Test directory prepared with multiple album subdirectories

---

## Test Cases

### Test 1: Multi-Album Detection (CRITICAL)
**Setup**: Directory with 3 album subdirectories
**Steps**:
1. Load directory with 3 albums
2. Verify per-album banner appears
3. Verify 3 albums listed with detection results
4. Verify checkboxes for each album
5. Verify expand/collapse buttons work

**Expected**: ✅ Per-album banner shows 3 albums with correct detection

---

### Test 2: Album Selection and Preview (CRITICAL)
**Setup**: Same 3-album directory
**Steps**:
1. Select 2 albums (check boxes)
2. Leave 1 album unchecked
3. Click "Apply to Selected"
4. Verify previews generated
5. Check preview column for each file

**Expected**:
- ✅ Selected albums show smart template in preview
- ✅ Unselected album shows global template in preview
- ✅ Button disabled during preview loading

---

### Test 3: Rename Operation (CRITICAL)
**Setup**: Same directory after applying templates
**Steps**:
1. Select all files
2. Click Rename
3. Wait for completion
4. Verify renamed files

**Expected**:
- ✅ Selected album files renamed with smart template
- ✅ Unselected album files renamed with global template
- ✅ No errors during rename

---

### Test 4: Quick Actions
**Setup**: 5-album directory
**Steps**:
1. Click "Select All" → verify all checked
2. Click "Deselect All" → verify all unchecked
3. Check 2 albums manually
4. Click "Invert Selection" → verify 3 checked, 2 unchecked

**Expected**: ✅ All quick actions work correctly

---

### Test 5: Banner Dismissal
**Setup**: Multi-album directory
**Steps**:
1. Show per-album banner
2. Click X button
3. Verify banner hidden
4. Reload directory
5. Verify banner shows again (not permanently dismissed)

**Expected**: ✅ Banner dismisses temporarily, reappears on new load

---

### Test 6: Feature Flag OFF (Regression Test)
**Setup**: Feature flag disabled
**Steps**:
1. Disable per-album detection in settings
2. Reload directory with multiple albums
3. Verify single-banner shown (not per-album)

**Expected**: ✅ Falls back to single-banner mode (current behavior)

---

### Test 7: Single Album (Edge Case)
**Setup**: Directory with only 1 album
**Steps**:
1. Load single-album directory
2. Verify single-banner shown (not per-album)

**Expected**: ✅ Shows single-banner for 1 album

---

### Test 8: 100+ Albums (Performance)
**Setup**: Directory with 100+ subdirectories
**Steps**:
1. Load massive directory
2. Check console for warning
3. Verify only 100 albums analyzed
4. Check performance (< 2 seconds)

**Expected**:
- ✅ Warning shown
- ✅ Limited to 100 albums
- ✅ Acceptable performance

---

### Test 9: Detection Errors (Error Handling)
**Setup**: Directory with corrupted files
**Steps**:
1. Load directory with 1 corrupted album
2. Verify partial results shown
3. Verify other albums work

**Expected**: ✅ Graceful degradation, other albums work

---

### Test 10: State Clearing (Race Condition)
**Setup**: Two different directories
**Steps**:
1. Load directory A
2. Select albums
3. Immediately load directory B
4. Verify no state from A

**Expected**: ✅ State cleared, no stale data

---

## Quick Test (5 minutes)

**Essential tests only**:
- Test 1: Multi-album detection shows
- Test 2: Selection and preview works
- Test 3: Rename applies correct templates
- Test 6: Feature flag OFF works

**Pass Criteria**: All 4 tests pass with no errors

---

## Full Test (30 minutes)

**All 10 tests** + exploratory testing

**Pass Criteria**: 9/10 tests pass (1 minor issue acceptable)

---

## Testing Checklist

**Before Testing**:
- [ ] Backend deployed
- [ ] Frontend deployed
- [ ] Feature flag accessible in settings
- [ ] Test data prepared (multiple album directories)

**During Testing**:
- [ ] Record all errors in console
- [ ] Screenshot any UI issues
- [ ] Note performance issues
- [ ] Test on different browsers (Chrome, Firefox, Safari)

**After Testing**:
- [ ] Document any bugs found
- [ ] Verify all critical tests pass
- [ ] Report results

---

## Known Limitations

1. Maximum 100 albums analyzed (performance limit)
2. First-level subdirectories only (nested treated as parent)
3. No selection persistence across reloads
4. Preview generation sequential (not parallel)

---

## Test Status

**Last Test Date**: Not yet tested
**Test Result**: Pending
**Tester**: TBD
**Pass Rate**: TBD

---

**Status**: ✅ Test Plan Complete
**Next**: User testing
