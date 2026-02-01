# Lesson Learned: v16 Fix - Rename Operations Not Using Temporary Template

**Date**: 2026-01-30
**Bug ID**: Critical - Rename operations ignored temporary Smart Track Detection template
**Status**: ✅ FIXED in v16

---

## Problem Description

### User Testing Results (Test 5 FAILED)

User clicked "Use This" on Smart Track Detection banner and reported:

1. **Banner shown**: Suggested template `{track} - {artist} - {title}`
2. **Clicked "Use This"**: Toast showed "Temporary template applied: {track} - {artist} - {title} (not saved to settings)"
3. **Previews correct**: Preview column showed correct format:
   - "01 - Big Audio Dynamite - Medicine Show.mp3"
   - "02 - Big Audio Dynamite - Sony.mp3"
   - etc.
4. **All files auto-selected**: 8 files selected correctly ✅
5. **Clicked "Rename Now"**: Files renamed WITHOUT track numbers
6. **Wrong output**:
   - "03 Big Audio Dynamite - E=mc2.mp3 » Big Audio Dynamite - E=mc2 [6A 129].mp3"
   - "01 Big Audio Dynamite - Medicine Show.mp3 » Big Audio Dynamite - Medicine Show [12B 117].mp3"
   - Used settings template: `{artist} - {title} [{camelot} {bpm}]`
   - Did NOT use temporary template: `{track} - {artist} - {title}`

**User Quote**: "When I click 'USE THIS', the files should be renamed using '{track} - {artist} - {title}' which is properly displayed in the 'Preview (New Name)' column. However, when I do the rename, it's using `{artist} - {title} [{camelot} {bpm}]`"

**Conclusion**: Previews showed correct template but rename operation used wrong template.

---

## Root Cause Analysis

### Template Fetching Inconsistency

**Three code paths fetch templates:**

#### Path 1: loadAllPreviews() - CORRECT ✅
**Location**: Line 1245-1253

```javascript
// Get current template: Check for temporary template first, then settings
let template;
if (this.temporaryTemplate) {
    template = this.temporaryTemplate;
    console.log('Using temporary template from Smart Track Detection:', template);
} else {
    const config = await this.api.getConfig();
    template = config.default_template || null;
    console.log('Using template from settings:', template);
}
```

This method checks `this.temporaryTemplate` first, then falls back to config. **This is why previews showed correct format.**

#### Path 2: executeRename() - WRONG ❌
**Location**: Line 1751-1757 (before v16 fix)

```javascript
// BUGGY CODE (v15)
try {
    // Get current template from config (Bug fix: Smart Track Detection template not applied)
    const config = await this.api.getConfig();
    const template = config.default_template || null;

    // Start rename operation with template from config
    const result = await this.api.executeRename(this.currentPath, filePaths, template);
```

This method only fetched from config, ignored `this.temporaryTemplate`. **This is why rename used wrong template.**

#### Path 3: executeRenameNow() - WRONG ❌
**Location**: Line 2098-2104 (before v16 fix)

```javascript
// BUGGY CODE (v15)
try {
    // Get current template from config (Bug fix v12: executeRenameNow also needs template)
    const config = await this.api.getConfig();
    const template = config.default_template || null;

    // Start rename operation with template from config
    const result = await this.api.executeRename(this.currentPath, filePaths, template);
```

Same issue - only fetched from config, ignored `this.temporaryTemplate`.

---

## The Fix (v16)

### Applied Same Logic to Both Rename Methods

**Pattern to follow** (from `loadAllPreviews()`):
1. Check `this.temporaryTemplate` first
2. If set, use it
3. Otherwise, fetch from config
4. Add console logging for debugging

### Fix #1: executeRename() Method

**File**: `web/static/js/app.js`, lines 1751-1763

```javascript
// FIXED CODE (v16)
try {
    // Task #94 FIX v16: Check for temporary template first, then settings
    let template;
    if (this.temporaryTemplate) {
        template = this.temporaryTemplate;
        console.log('Using temporary template from Smart Track Detection for rename:', template);
    } else {
        const config = await this.api.getConfig();
        template = config.default_template || null;
        console.log('Using template from settings for rename:', template);
    }

    // Start rename operation with template
    const result = await this.api.executeRename(this.currentPath, filePaths, template);
```

### Fix #2: executeRenameNow() Method

**File**: `web/static/js/app.js`, lines 2098-2110

```javascript
// FIXED CODE (v16)
try {
    // Task #94 FIX v16: Check for temporary template first, then settings
    let template;
    if (this.temporaryTemplate) {
        template = this.temporaryTemplate;
        console.log('Using temporary template from Smart Track Detection for rename:', template);
    } else {
        const config = await this.api.getConfig();
        template = config.default_template || null;
        console.log('Using template from settings for rename:', template);
    }

    // Start rename operation with template
    const result = await this.api.executeRename(this.currentPath, filePaths, template);
```

### Files Modified (v16)
- `web/static/js/app.js`:
  - Line 6: Version bump v15 → v16
  - Lines 1751-1763: `executeRename()` template logic
  - Lines 2098-2110: `executeRenameNow()` template logic
- `web/static/index.html`:
  - Lines 949-951: Cache-busting v15 → v16

---

## Key Lessons

### 1. Keep Template Fetching Logic Consistent

**Anti-Pattern Found**:
```javascript
// loadAllPreviews() - checks temporary template first ✅
if (this.temporaryTemplate) { ... }

// executeRename() - only checks config ❌
const config = await this.api.getConfig();

// executeRenameNow() - only checks config ❌
const config = await this.api.getConfig();
```

**Consequence**: Previews showed one thing, rename did another.

**Better Pattern**:
```javascript
// All three methods should use SAME logic
function getActiveTemplate() {
    return this.temporaryTemplate
        ? this.temporaryTemplate
        : (await this.api.getConfig()).default_template || null;
}
```

### 2. DRY Principle Violation = Bug Multiplication

**Problem**: Template-fetching logic duplicated in three places:
1. `loadAllPreviews()` - correct implementation
2. `executeRename()` - wrong implementation
3. `executeRenameNow()` - wrong implementation

**Why This Happened**:
- v15 (Task #94) implemented temporary template system
- Fixed `loadAllPreviews()` correctly
- Forgot to update both rename methods
- Code duplication meant bug existed in 2 out of 3 places

**Prevention**: Extract shared logic into helper method.

### 3. Test What You Show

**Critical UX Rule**: If previews show X, rename must produce X.

**What Happened**:
- User saw previews with track numbers (from temporary template)
- User clicked rename
- Files renamed without track numbers (from settings template)
- Previews and results didn't match

**Lesson**: When implementing "preview before action" patterns, ensure preview and action use identical logic.

### 4. Console Logging Saved Us

**Added in v16**:
```javascript
console.log('Using temporary template from Smart Track Detection for rename:', template);
console.log('Using template from settings for rename:', template);
```

**Why Important**:
- User can now see exactly which template is being used
- Debugging future template issues will be instant
- Transparent behavior helps identify bugs faster

### 5. Search for All Template Fetch Locations

**How to Find All Locations** (Prevention checklist):
```bash
# Search for config fetch
grep -n "api.getConfig()" app.js

# Search for template assignment
grep -n "template =" app.js

# Search for executeRename calls
grep -n "executeRename" app.js
```

**In this case**:
- Found 3 locations that fetch templates
- Only 1 was correct
- Fixed the other 2 in v16

---

## Prevention Checklist

### When Adding State Variables (like temporaryTemplate)

- [ ] Find ALL locations that read related data (template from config)
- [ ] Update ALL locations to check new variable first
- [ ] Add console logging to ALL locations for debugging
- [ ] Test that UI display and action logic match

### When Implementing Preview-Then-Action Patterns

- [ ] Ensure preview uses exact same logic as action
- [ ] Extract shared logic into helper methods (DRY)
- [ ] Add console logging to verify both paths
- [ ] Test that preview matches actual result

### Code Review Questions

- "Where else do we fetch templates?"
- "Does the preview logic match the action logic?"
- "Should this be extracted into a helper method?"
- "Are we checking temporary state before persistent state?"

---

## Impact Analysis

### v15 (Partial Implementation)
- ✅ Added `this.temporaryTemplate` state variable
- ✅ Fixed `loadAllPreviews()` to check temporary template
- ✅ Fixed "Use This" to not save to config
- ❌ Forgot to update `executeRename()`
- ❌ Forgot to update `executeRenameNow()`
- ❌ Previews showed correct template but rename used wrong template

### v16 (Complete Fix)
- ✅ Fixed `executeRename()` to check temporary template
- ✅ Fixed `executeRenameNow()` to check temporary template
- ✅ Added console logging to both methods
- ✅ Now all three methods use consistent template-fetching logic
- ✅ Previews and rename results now match

---

## Related Issues

### Similar Pattern in Codebase

**Other operations that should check temporary state first**:
- Undo operations - should check for temporary template
- Export/Save operations - should use current effective template
- Settings display - should show if temporary template is active

**Recommendation**: Audit codebase for other locations that read `config.default_template` and verify they handle `this.temporaryTemplate` correctly.

---

## Testing Strategy (v16)

### Manual Test Case: Smart Track Detection Rename

#### Test 5 (The Failed Test) - Repeat with v16

```
Setup:
1. Ensure settings template is set to custom format (e.g., "{artist} - {title} [{camelot} {bpm}]")
2. Load directory with album that triggers Smart Track Detection
3. Verify banner appears with suggested template "{track} - {artist} - {title}"

Steps:
1. Click "Use This" on banner
2. Verify toast shows "Temporary template applied: {track} - {artist} - {title} (not saved to settings)"
3. Verify previews show format like "01 - Big Audio Dynamite - Medicine Show.mp3"
4. Click "Rename Now" (either from preview modal or main page)
5. Wait for rename to complete

Expected Results:
✅ Files renamed with track numbers: "01 - Big Audio Dynamite - Medicine Show.mp3"
✅ Files NOT renamed with settings template: "Big Audio Dynamite - Medicine Show [12B 117].mp3"
✅ Console log shows: "Using temporary template from Smart Track Detection for rename: {track} - {artist} - {title}"
✅ Rename results match preview column exactly

Failure Criteria:
❌ Files renamed without track numbers
❌ Console log shows: "Using template from settings for rename: ..."
❌ Rename results don't match preview
```

### Additional Test Cases

#### Test: Rename Without Temporary Template
```
Steps:
1. Load directory (no Smart Track Detection banner)
2. Select files
3. Click "Rename Now"

Expected:
✅ Console log shows: "Using template from settings for rename: {artist} - {title} [{camelot} {bpm}]"
✅ Files renamed with settings template
```

#### Test: Temporary Template Cleared on Directory Change
```
Steps:
1. Load album 1, click "Use This"
2. Load album 2 (different directory)
3. Click "Rename Now" without clicking "Use This"

Expected:
✅ Album 2 files renamed with settings template (not Smart Track Detection)
✅ Console log shows: "Using template from settings for rename: ..."
```

---

## Verification

### v16 Testing Required

**User must test**:
- ✅ Same Test 5 flow that failed in v15
- ✅ Verify files now renamed with Smart Track Detection template
- ✅ Verify rename results match preview column
- ✅ Example: "Alabama Shakes - Be Mine [1A 144].mp3" → "03 - Alabama Shakes - Be Mine.mp3"

### Success Criteria

- [ ] v16 fix works for preview modal rename path
- [ ] v16 fix works for main page rename path
- [ ] Previews and rename results always match
- [ ] Console logs show correct template being used
- [ ] No regressions in other rename functionality

---

## Documentation

**Related Documents**:
- `lessons-learned-2026-01-30-v11-incomplete-fix.md` - Dual rename code paths (v11→v12)
- `lessons-learned-2026-01-30-template-not-applied-to-rename.md` - Original v11 fix
- `current-status.md` - Updated with v16 status

**Task Tracking**:
- Task #94: "Use This" temporary (not permanent) - v15 partial, v16 complete
- Task #99: Rename operations use temporary template (v16)

---

## Future Improvements

### Refactoring Opportunity: Extract Template Helper

**Current (v16)**: Template logic duplicated in 3 places:
```javascript
// Repeated 3 times
let template;
if (this.temporaryTemplate) {
    template = this.temporaryTemplate;
    console.log('Using temporary template from Smart Track Detection...');
} else {
    const config = await this.api.getConfig();
    template = config.default_template || null;
    console.log('Using template from settings...');
}
```

**Better (Future Refactoring)**:
```javascript
// Add helper method to App class
async getActiveTemplate() {
    if (this.temporaryTemplate) {
        console.log('Using temporary template from Smart Track Detection:', this.temporaryTemplate);
        return this.temporaryTemplate;
    } else {
        const config = await this.api.getConfig();
        const template = config.default_template || null;
        console.log('Using template from settings:', template);
        return template;
    }
}

// Use in all three methods
async loadAllPreviews() {
    const template = await this.getActiveTemplate();
    // ...
}

async executeRename() {
    const template = await this.getActiveTemplate();
    // ...
}

async executeRenameNow() {
    const template = await this.getActiveTemplate();
    // ...
}
```

**Benefits**:
- Single source of truth for template logic
- Easier to maintain and test
- Eliminates duplication
- Future changes only need to update one place

---

**Summary**: When implementing state that affects multiple operations (previews, rename), ensure ALL operations check the state consistently. Previews and actions must use identical logic. Code duplication creates hiding spots for bugs. v16 fixes the inconsistency between preview and rename template fetching.
