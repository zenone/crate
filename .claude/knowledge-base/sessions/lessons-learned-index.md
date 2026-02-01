# Lessons Learned - Index

**Project**: Crate (DJ MP3 Renamer)
**Last Updated**: 2026-01-30

This index provides quick access to all lessons learned during development. Each lesson learned document captures bugs, root causes, fixes, and prevention strategies.

---

## 📚 All Lessons Learned

### 2026-01-30 Session

#### 1. Smart Track Detection Template Not Applied to Rename ⭐ CRITICAL
**File**: `lessons-learned-2026-01-30-template-not-applied-to-rename.md`
**Category**: Frontend API Integration
**Severity**: Critical - Broke primary user workflow

**Summary**: When user clicked "Use This" on Smart Track Detection banner, the template was saved to config but NOT used during rename operation. Files were renamed using old template instead.

**Root Cause**: `executeRename()` method didn't fetch config before calling API, unlike `loadAllPreviews()` which correctly fetched config.

**Key Lesson**: Always fetch config before API calls that use config values. Match patterns across similar operations (if preview fetches config, rename should too).

**Prevention**:
- Code review checklist: Does operation fetch config?
- Test full workflow, not just preview
- Compare with similar working operations

---

#### 2. Smart Track Detection Banner Positioning
**File**: `lessons-learned-2026-01-30-banner-positioning.md`
**Category**: UX/Visual Design
**Severity**: High - Feature appeared broken due to poor UX

**Summary**: User reported "Smart track detection did not work" after loading album. Feature WAS working, but banner appeared at bottom of page (below all files), making it invisible without scrolling.

**Root Cause**: Banner HTML positioned at line 225 in index.html (after file list container closes), instead of at top of content area.

**Key Lesson**: Feature functionality is worthless if users can't see it. Always consider visibility and positioning for notification/suggestion UI elements.

**Prevention**:
- Place important UI elements "above the fold"
- Test with realistic data (many files that require scrolling)
- Visual debugging: Ask for screenshots when feature "doesn't work"

---

### Common Patterns & Best Practices

#### Pattern: Fetching Config for API Calls
```javascript
// ✅ CORRECT PATTERN
const config = await this.api.getConfig();
const template = config.default_template || null;
const result = await this.api.someOperation(path, files, template);

// ❌ INCORRECT PATTERN
const result = await this.api.someOperation(path, files);
// ^ Missing template - defaults to null, backend may use stale config
```

**Locations Using This Pattern**:
- `loadAllPreviews()` (line 1245 in app.js) ✅
- `executeRename()` (line 1733 in app.js) ✅ Fixed in v11
- `saveSettings()` (line 2226 in app.js) ✅

---

#### Pattern: Banner/Notification Positioning

**Best Practice**: Place important notifications at TOP of content area

```html
<!-- ✅ CORRECT: Banner at top, immediately visible -->
<div id="metadata-progress">...</div>
<div id="smart-suggestion-banner">...</div> <!-- Here! -->
<div id="file-list-container">...</div>

<!-- ❌ INCORRECT: Banner at bottom, requires scrolling -->
<div id="file-list-container">...</div>
<div id="smart-suggestion-banner">...</div> <!-- Hidden below files -->
```

---

#### Pattern: Async Metadata Loading

**Best Practice**: Wait for all metadata before running analysis

```javascript
// ✅ CORRECT: Wait for all metadata promises
const metadataPromises = this.currentFiles
    .map(f => f._metadataPromise)
    .filter(p => p);

if (metadataPromises.length > 0) {
    await Promise.all(metadataPromises);
    console.log('✓ All metadata loaded');
}

await this.analyzeAndShowSuggestion();

// ❌ INCORRECT: Run analysis immediately
await this.analyzeAndShowSuggestion();
// ^ Metadata not loaded yet, analysis runs on incomplete data
```

---

## 📊 Statistics

### Session: 2026-01-30
- **Total Lessons Learned**: 2
- **Critical Bugs Fixed**: 2
- **User-Reported Issues**: 2
- **Root Cause Categories**:
  - Frontend API Integration: 1
  - UX/Positioning: 1

### Impact Analysis
- **Critical** (blocks workflow): 1
- **High** (poor UX, feature appears broken): 1
- **Medium**: 0
- **Low**: 0

---

## 🔍 Quick Reference

### By Category

**Frontend/API Integration**:
- Smart Track Detection template not applied to rename

**UX/Visual Design**:
- Smart Track Detection banner positioning

**Async/Timing Issues**:
- Smart Track Detection metadata timing (from earlier sessions)

---

## 📖 How to Use This Index

### When Implementing New Features
1. Check if similar feature exists (e.g., preview vs rename)
2. Look for lessons learned in same category
3. Apply best practices from lessons learned
4. Add to code review checklist

### When Debugging
1. Search this index for similar symptoms
2. Read the relevant lesson learned document
3. Apply the same debugging techniques
4. Document new lesson if novel issue

### When Onboarding
1. Read all lesson learned documents
2. Note common patterns and anti-patterns
3. Review prevention checklists
4. Apply to code reviews

---

## 🎯 Next Steps

### Ongoing Documentation
- [ ] Add lesson learned for any new bugs discovered
- [ ] Update this index with new entries
- [ ] Review lessons learned during code reviews
- [ ] Create automated checks based on common patterns

### Knowledge Sharing
- [ ] Share lessons learned in team meetings
- [ ] Add to developer onboarding docs
- [ ] Create linting rules for common anti-patterns
- [ ] Build automated tests for prevention strategies

---

**Note**: Each lesson learned document follows this structure:
1. Problem Description (user report)
2. Root Cause Analysis (technical details)
3. The Fix (code changes)
4. Key Lessons (takeaways)
5. Prevention (checklist/best practices)
6. Verification (test results)

This consistent structure makes lessons easy to reference and apply.
