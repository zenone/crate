# Business Logic: Low-Friction Smart Detection

**Created**: 2026-02-01
**Session**: Cancel Buttons + Auto-Apply UX Improvements
**User Request**: Reduce friction for large batch operations (100+ albums)

---

## 🎯 Problem Statement

### Current Issues (User Feedback)

**Issue #1: No Cancel Button** (Image #1 - Screenshot)
- User loads directory → sees "Loading metadata: 15/57 files (26%) - ~1m 51s remaining"
- **NO WAY TO CANCEL** if user selected wrong directory
- Must wait for entire operation to complete (bad UX)

**Issue #2: High-Friction Smart Detection** (Image #2 - Screenshot)
- Every suggestion shows banner with "Use This" / "Ignore" buttons
- User must **manually click for EVERY album** = HIGH FRICTION
- Example: Scan 100 albums → must click 100 times (terrible UX for batch operations)

### User's Vision

> "What if a user scans 10 album directories. 2 of the directories should get detected by smart track detection as needing to start the filenames with the track numbers. The other 8, for this example, do not and filenames can be whatever the user selected as the filename template in the config. The user shouldn't have to click yes or no (use this or ignore) for each album, as they seems like a bad UX with lots of friction, especially for a user who wants to scan a large repository of songs."

**Key Insight**: High-confidence suggestions should **auto-apply** with minimal user interaction.

---

## ✅ Solution Design

### Part 1: Cancel Buttons (Tasks #126, #127)

**When Cancel Appears**:
- ✅ During metadata loading (progress bar visible)
- ✅ During preview generation (preview progress visible)
- ❌ NOT during idle state (no operations running)

**Where to Place**:
- **Inside progress bar** next to percentage text
- Small red "✕ Cancel" button or icon button
- Visible during operation, hidden when complete

**Cancel Behavior**:
1. **Abort current operation** (use AbortController)
2. **Keep partial results** (don't clear loaded files/previews)
3. **Hide progress bar**
4. **Show notification**: "Operation cancelled - X items loaded"
5. **Log to console** for debugging

**Edge Cases**:
| Scenario | Behavior |
|----------|----------|
| Cancel after 1 file loaded | Keep that 1 file in table |
| Cancel during preview | Keep partial previews, rest stay blank |
| Cancel then reload same dir | Fresh start (previous load cleared) |
| Cancel during auto-apply | Abort auto-apply, show banner instead |

---

### Part 2: Auto-Apply Logic (Tasks #128, #129)

**Core Principle**: **High confidence = auto-apply**, **Medium/Low = show banner for review**

#### Decision Matrix: Single Template Suggestions

| Confidence | Threshold | Action | Banner | User Interaction |
|-----------|-----------|--------|--------|------------------|
| **High** | >= 0.9 | **Auto-apply template** | No (toast only) | None (or dismiss toast) |
| **Medium** | >= 0.7 | Pre-select "Use This" | Yes (recommended) | Can dismiss or change |
| **Low** | < 0.7 | Show banner | Yes (no pre-selection) | Must review |

**Example Flow (High Confidence)**:
```
1. User loads directory
2. Metadata loads → Smart Detection analyzes
3. Confidence = 0.95 (HIGH)
4. Frontend auto-applies template to this.temporaryTemplate
5. Auto-loads previews with new template
6. Shows toast: "✓ Smart suggestion applied: {artist} - {title} [0{track}]"
7. Toast has [Undo] button (reverts to previous template)
8. No banner shown (low friction!)
```

**Example Flow (Medium Confidence)**:
```
1. User loads directory
2. Metadata loads → Smart Detection analyzes
3. Confidence = 0.75 (MEDIUM)
4. Shows banner with "Use This" button highlighted
5. User can click "Use This" or "Ignore"
6. If user clicks "Use This" → applies template + loads previews
```

---

#### Decision Matrix: Per-Album Detection

| Scenario | Action | Checkboxes | User Interaction |
|----------|--------|-----------|------------------|
| **All albums high confidence** | Auto-check all | ✓ All checked | Click "Apply to Selected" (1 click) |
| **2 high, 8 low** (user's example) | Auto-check 2 high only | ✓ 2 checked, ☐ 8 unchecked | Review + click "Apply" (1 click) |
| **All albums low confidence** | None checked | ☐ All unchecked | Review + manually check (N clicks) |
| **Mixed confidence** | Check high only | ✓ High checked, ☐ others | Review + adjust (1-N clicks) |

**Example Flow (User's 10-Album Scenario)**:
```
1. User loads directory with 10 album subdirectories
2. Metadata loads → Per-Album Detection analyzes
3. Results:
   - Album A: confidence = 0.95 (HIGH) → needs track numbers
   - Album B: confidence = 0.92 (HIGH) → needs track numbers
   - Albums C-J: confidence = 0.5 (LOW) → don't need track numbers
4. Banner shows with:
   ✓ Album A (HIGH confidence, auto-checked)
   ✓ Album B (HIGH confidence, auto-checked)
   ☐ Album C (LOW confidence, unchecked)
   ☐ Album D (LOW confidence, unchecked)
   ... (etc)
5. User reviews: "Looks good!"
6. User clicks "Apply to Selected" → ONLY albums A & B get track number templates
7. Total clicks: 1 (vs 10 in current implementation)
```

---

### Part 3: Toast Notification System (Task #130)

**Why Toast Notifications?**
- Auto-apply is **silent** (no banner) → user needs to know what happened
- Toast = **non-intrusive**, dismissible, provides awareness
- Alternative to showing banner for every high-confidence suggestion

**Toast Design**:
```
┌─────────────────────────────────────────────┐
│ ✓ Smart suggestion applied                  │
│ Template: {artist} - {title} [0{track}]     │
│ [Undo] [Dismiss]                            │
└─────────────────────────────────────────────┘
```

**Toast Behavior**:
- Appears **top-right corner** (non-blocking)
- **Auto-dismisses after 5 seconds**
- Click **[Undo]** → reverts template change
- Click **[Dismiss]** → hides immediately
- **Stack multiple toasts** if multiple auto-applies

**Use Cases**:
| Event | Toast Message |
|-------|--------------|
| Auto-applied single template | "✓ Smart suggestion applied: {template}" |
| Auto-selected albums | "✓ 2 albums auto-selected (high confidence)" |
| Cancelled operation | "⚠ Operation cancelled - 15/57 files loaded" |
| Error during auto-apply | "✗ Auto-apply failed: {error}" |

---

## 🔧 Backend Confidence Levels (Task #132 ✅)

**Already Implemented!** Backend returns confidence levels:

### Per-Album Detection
```python
# crate/core/context_detection.py:604-609
if context.confidence >= 0.9:
    confidence_str = "high"
elif context.confidence >= 0.7:
    confidence_str = "medium"
else:
    confidence_str = "low"

# Response format:
{
    "detection": {
        "confidence": "high",  # String: "high" | "medium" | "low"
        "suggested_template": "{artist} - {title} [0{track}]"
    }
}
```

### Single Template Suggestion
```python
# crate/core/context_detection.py:424
return {
    "confidence": best_context.confidence  # Float: 0.0-1.0
}

# Example response:
{
    "template": "{artist} - {title}",
    "confidence": 0.95  # Float
}
```

**Frontend Action Required**:
- Convert float to string using same thresholds:
  - `confidence >= 0.9` → "high"
  - `confidence >= 0.7` → "medium"
  - `confidence < 0.7` → "low"

---

## 🚨 Edge Cases & Safety Measures

### Race Conditions
| Scenario | Handling |
|----------|----------|
| Cancel during metadata load | AbortController aborts fetch, keeps partial results |
| Cancel during preview | Existing `previewAbortController` handles this |
| Auto-apply during metadata load | Wait for metadata promises before auto-apply |
| User changes template after auto-apply | Respect user choice (user template wins) |
| Multiple suggestions in sequence | Last suggestion wins (or highest confidence?) |

### Error Handling
| Failure Mode | Graceful Degradation |
|-------------|---------------------|
| Auto-apply fails | Fall back to showing banner |
| Toast notification fails | Log error, don't break workflow |
| Confidence missing from backend | Default to "low" (show banner) |
| Cancel aborts mid-operation | Keep partial results, log cancellation |

### Feature Flags (Safe Rollout)
```javascript
// Configuration options
enable_smart_auto_apply: false  // Default: disabled (opt-in for safety)
auto_apply_confidence_threshold: 0.9  // Only auto-apply if >= 0.9
enable_per_album_auto_select: false  // Default: disabled (opt-in)
show_auto_apply_notifications: true  // Show toast for auto-applied suggestions
```

---

## 📊 User Workflows: Before vs After

### Workflow 1: Single Album (57 Files)

**BEFORE** (Current):
1. Load directory → see "(loading...)" in preview column
2. Wait for metadata to load (1 min)
3. Banner appears: "Recommended: {artist} - {title}"
4. Click "Use This" button → previews reload
5. Review previews → click "Preview Rename" or "Rename Now"
6. **Total clicks: 2-3**

**AFTER** (With Auto-Apply):
1. Load directory → metadata loads automatically
2. Auto-apply detects HIGH confidence → auto-applies template
3. Previews load automatically with new template
4. Toast appears: "✓ Smart suggestion applied: {artist} - {title}"
5. User reviews previews → click "Rename Now"
6. **Total clicks: 1** (50-66% reduction)

---

### Workflow 2: Multiple Albums (100 Albums)

**BEFORE** (Current):
1. Load directory with 100 album subdirectories
2. Wait for metadata to load (5-10 min)
3. Per-album banner appears with 100 checkboxes (all unchecked)
4. User must manually check each album that needs track numbers (e.g., 20 albums)
5. Click "Apply to Selected"
6. Wait for previews to reload
7. **Total clicks: 21** (20 checkboxes + 1 apply button)

**AFTER** (With Auto-Select):
1. Load directory with 100 album subdirectories
2. Wait for metadata to load (5-10 min)
3. Per-album banner appears:
   - 20 HIGH confidence albums → **auto-checked ✓**
   - 80 LOW confidence albums → unchecked ☐
4. User reviews: "Looks good!"
5. Click "Apply to Selected" → only 20 albums get templates
6. **Total clicks: 1** (95% reduction!)

---

## 🧪 Testing Approach (Task #133)

### Test Scenarios

**Cancel Button Tests**:
- [ ] Load 100-file directory → cancel at 50% → verify 50 files loaded
- [ ] Load directory → cancel immediately → verify graceful abort
- [ ] Start preview → cancel at 25% → verify partial previews shown
- [ ] Cancel then reload same directory → verify fresh start

**Auto-Apply Tests (Single Template)**:
- [ ] High confidence (0.95) → verify auto-applied, toast shown, no banner
- [ ] Medium confidence (0.75) → verify banner shown, "Use This" pre-selected
- [ ] Low confidence (0.5) → verify banner shown, no pre-selection

**Auto-Apply Tests (Per-Album)**:
- [ ] 10 albums, all high (0.9+) → verify all checked
- [ ] 10 albums, 2 high + 8 low → verify 2 checked, 8 unchecked
- [ ] 10 albums, all low → verify none checked

**Edge Case Tests**:
- [ ] Cancel during auto-apply → verify safe abort
- [ ] Change template after auto-apply → verify user choice respected
- [ ] Backend returns no confidence → verify defaults to "low" (show banner)
- [ ] Auto-apply fails → verify fallback to banner

**Performance Tests**:
- [ ] 1000 files → measure cancel responsiveness (< 500ms)
- [ ] 100 albums → measure auto-selection performance (< 1s)
- [ ] Toast stacking → verify 5+ toasts don't block UI

---

## 🎨 UI/UX Specifications

### Cancel Button Design

**Metadata Progress Bar**:
```
┌────────────────────────────────────────────────────────────┐
│ 🔄 Loading metadata: 15/57 files (26%) - ~1m 51s remaining │
│ ▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░  [✕ Cancel]                   │
└────────────────────────────────────────────────────────────┘
```

**Preview Progress Bar**:
```
┌────────────────────────────────────────────────────────────┐
│ 👁️ Generating previews: 25/57 files (44%)  [✕ Cancel]     │
│ ▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░                               │
└────────────────────────────────────────────────────────────┘
```

### Toast Notification Design

**Auto-Apply Success**:
```
┌─────────────────────────────────────────────┐
│ ✓ Smart suggestion applied                  │
│ Template: {artist} - {title} [0{track}]     │
│ [Undo] [Dismiss]                            │
└─────────────────────────────────────────────┘
```

**Per-Album Auto-Select**:
```
┌─────────────────────────────────────────────┐
│ ✓ 2 albums auto-selected                    │
│ High confidence track numbering detected    │
│ [Dismiss]                                   │
└─────────────────────────────────────────────┘
```

**Operation Cancelled**:
```
┌─────────────────────────────────────────────┐
│ ⚠ Operation cancelled                       │
│ 15/57 files loaded                          │
│ [Dismiss]                                   │
└─────────────────────────────────────────────┘
```

---

## 🚀 Implementation Priority

### Phase 1: Cancel Buttons (Low Risk)
1. Task #126: Cancel metadata loading ⚡ **HIGH PRIORITY**
2. Task #127: Cancel preview generation ⚡ **HIGH PRIORITY**

**Why First**: Safer, less complex, immediate user benefit

### Phase 2: Auto-Apply (Medium Risk)
3. Task #130: Toast notification system 🔧 **FOUNDATION**
4. Task #128: Auto-apply single template 🎯 **CORE FEATURE**
5. Task #129: Auto-select per-album 🎯 **CORE FEATURE**

**Why Second**: More complex, needs feature flags, requires testing

### Phase 3: Documentation & Testing
6. Task #131: Update business logic docs 📝 **DOCUMENTATION**
7. Task #133: Test with real data 🧪 **VALIDATION**

---

## 📋 Rollback Plan

### If Auto-Apply Causes Issues

**Disable Feature Flags**:
```javascript
enable_smart_auto_apply: false  // Revert to manual banner
enable_per_album_auto_select: false  // Revert to manual checkboxes
```

**User Impact**: Returns to current behavior (show banner for all suggestions)

### If Cancel Buttons Cause Issues

**Hide Cancel Buttons**:
```css
.cancel-button {
    display: none;  /* Hide cancel buttons */
}
```

**User Impact**: Returns to current behavior (wait for completion)

---

## 📖 Lessons Learned

### What Works
✅ **Auto-preview** (Task #125) reduced friction for small directories
✅ **Backend confidence levels** already implemented and accurate
✅ **Per-album detection** groups files correctly

### What Doesn't Scale
❌ **Manual clicks for every suggestion** = high friction for 100+ albums
❌ **No way to cancel long operations** = bad UX
❌ **All-or-nothing workflows** = doesn't accommodate mixed scenarios

### Design Principles Learned
1. **High confidence = automation** (reduce friction)
2. **Low confidence = manual review** (user control)
3. **Always provide awareness** (toast notifications, not silent)
4. **Always allow undo** (don't trap users in decisions)
5. **Always allow cancel** (respect user's time)
6. **Feature flags are critical** (safe rollout, easy rollback)

---

## 🎯 Success Metrics

### Quantitative
- Cancel button usage: Track how often users cancel operations
- Auto-apply rate: % of suggestions auto-applied vs manual
- Clicks reduced: Measure average clicks per workflow (before vs after)
- Time saved: Measure time from load → rename (before vs after)

### Qualitative
- User feedback: "This is much faster!" vs "Auto-apply was wrong"
- Error rate: Track confidence accuracy (high confidence = correct?)
- Undo rate: How often users undo auto-applied suggestions?

### Target Metrics
- **Cancel adoption**: 10%+ of loads cancelled (indicates usefulness)
- **Auto-apply accuracy**: 95%+ of auto-applied suggestions are correct
- **Clicks reduced**: 50%+ reduction for single album, 90%+ for multi-album
- **User satisfaction**: Positive feedback on low-friction workflow

---

**Status**: ✅ Business Logic Designed, Ready for Implementation
**Next Step**: Implement Phase 1 (Cancel Buttons) for immediate user benefit
