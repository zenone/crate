# Claude Coding Excellence Guide

**Last Updated**: 2026-01-30
**Purpose**: Comprehensive guide for Claude to write optimal code on first attempt
**Audience**: Future Claude instances working on this project
**Status**: Living document - continuously updated with lessons learned

---

## Table of Contents

1. [Philosophy & Principles](#philosophy--principles)
2. [The Pre-Coding Checklist](#the-pre-coding-checklist)
3. [Business Logic Analysis Framework](#business-logic-analysis-framework)
4. [User Journey Mapping](#user-journey-mapping)
5. [Side Effects Identification](#side-effects-identification)
6. [Technology Stack Selection](#technology-stack-selection)
7. [Implementation Best Practices](#implementation-best-practices)
8. [Testing & Verification](#testing--verification)
9. [Documentation Requirements](#documentation-requirements)
10. [Common Anti-Patterns to Avoid](#common-anti-patterns-to-avoid)
11. [Real-World Case Studies](#real-world-case-studies)
12. [Quick Reference](#quick-reference)

---

## Philosophy & Principles

### Core Philosophy

**"Think First, Code Second"**

Spending 5-10 minutes on upfront analysis saves 45+ minutes of iteration and rework.

### Guiding Principles

1. **Conservative Over Aggressive**
   - Give users explicit control
   - Avoid automatic actions
   - Minimize side effects
   - Safe defaults

2. **Complete Over Quick**
   - Map entire user journey before coding
   - Identify all side effects upfront
   - Clarify every uncertainty
   - Document decisions

3. **Simple Over Complex**
   - Avoid over-engineering
   - No premature abstractions
   - Solve current problem only
   - Three similar lines > complex abstraction

4. **Explicit Over Implicit**
   - User triggers actions
   - Clear feedback at each step
   - Obvious behavior
   - Predictable outcomes

5. **Trust But Verify**
   - User wants transparency
   - Document everything
   - Show reasoning
   - Enable verification

---

## The Pre-Coding Checklist

**STOP! Before writing ANY code, complete this checklist:**

### Phase 1: Understanding (5 minutes)

- [ ] **Read the request completely**
  - What is the user actually asking for?
  - What problem are they trying to solve?
  - Are there any ambiguities?

- [ ] **Identify the scope**
  - Is this a new feature, bug fix, or enhancement?
  - How many files will be affected?
  - What's the complexity level? (Low/Medium/High)

- [ ] **Check existing code**
  - Read relevant files BEFORE proposing changes
  - Understand current patterns and architecture
  - Identify related functionality

### Phase 2: Analysis (10-15 minutes for complex features)

- [ ] **Map complete user journey**
  - Start to finish, every step
  - "Then what?" after each action
  - Find natural stopping point

- [ ] **Identify ALL side effects**
  - Function calls triggered
  - API calls made
  - Data loaded
  - UI state changes
  - Computation costs

- [ ] **Clarify user intent**
  - What does user expect to happen?
  - What's the default behavior?
  - When should X happen vs Y?
  - Use AskUserQuestion if uncertain

- [ ] **Consider trade-offs**
  - Option A: Pros/Cons
  - Option B: Pros/Cons
  - Recommendation with reasoning

### Phase 3: Planning (5 minutes)

- [ ] **Document expected behavior**
  - Given: Initial state
  - When: User action
  - Then: System response
  - And: Next action

- [ ] **Define test cases**
  - Happy path
  - Edge cases
  - Error cases
  - Side effects verification

- [ ] **Choose implementation approach**
  - Conservative default selected
  - Risk level assessed
  - Rollback plan defined (if high risk)

### Ready to Code?

**If ANY checkbox unchecked → STOP and complete it first**

**If ANY uncertainty remains → Use AskUserQuestion**

**If multiple valid approaches → Present options to user**

---

## Business Logic Analysis Framework

### The "Then What?" Method

**Most bugs come from incomplete user journey analysis.**

For EVERY action, ask "Then what?" until you reach a natural stopping point.

#### Example: Task #84 (Remember Last Directory)

**Incomplete Analysis** (led to 3 iterations):
```
1. User closes app
2. User reopens app
3. App loads last directory path ← STOPPED HERE (TOO EARLY!)
```

**Complete Analysis** (should have done this):
```
1. User closes app
2. User reopens app
3. App loads last directory path
   → Then what? Auto-load files?
4. If auto-load: Files load into UI
   → Then what? Does renderFileList() run?
5. If renderFileList(): Does it auto-preview?
   → Then what? Does preview load metadata?
6. If load metadata: Expensive operation on startup
   → Then what? User sees "Why is this happening?"
7. CONCLUSION: Set path only, let user explicitly load
```

**Key Learning**: Continue asking "Then what?" until you understand the complete cascade of effects.

### Business Logic Template

Use this template for every feature:

```markdown
## Feature: [Name]

### User Problem
What problem does this solve?

### User Journey
1. User does X
2. System responds with Y
3. Then what? → [Next step]
4. Then what? → [Next step]
5. Continue until natural end

### Side Effects Analysis
For each system action:
- **Function calls**: [List]
- **API calls**: [List]
- **Data loads**: [What? How much?]
- **UI changes**: [What changes?]
- **Computation cost**: [Cheap/Expensive?]
- **User impact**: [What does user see/experience?]

### User Intent
- What does user expect?
- What's the default behavior?
- When should it be automatic vs explicit?
- What's the conservative choice?

### Implementation Options

#### Option A: [Name]
**Approach**: [Description]
**Pros**:
- [Pro 1]
- [Pro 2]
**Cons**:
- [Con 1]
- [Con 2]
**Side effects**: [List]
**User experience**: [Description]

#### Option B: [Name]
[Same structure]

### Recommendation
**Choice**: [Option X]
**Reasoning**: [Why this option?]
**Trade-offs**: [What we're accepting]

### Expected Behavior
**Given**: [Initial state]
**When**: [User action]
**Then**: [System response]
**And**: [Next action]

### Test Cases
1. **Happy path**: [Description]
2. **Edge case 1**: [Description]
3. **Error case**: [Description]
```

---

## User Journey Mapping

### How to Map User Journeys

**1. Start with trigger event**
- User clicks button
- User opens app
- User enters text
- System event

**2. Follow the chain**
```
Trigger Event
  ↓
System Action 1
  ↓ Then what?
System Action 2
  ↓ Then what?
System Action 3
  ↓ Then what?
User sees/experiences X
  ↓ Then what?
User does Y
  ↓ Then what?
Continue until natural end
```

**3. Branch for different paths**
```
Action X
  ↓
If condition A:
  → Path 1 → Then what?
If condition B:
  → Path 2 → Then what?
Error case:
  → Path 3 → Then what?
```

### Common Journey Patterns

**Pattern 1: User-Initiated Action**
```
User clicks button
  → Validate input
  → Show loading state
  → Make API call
  → Process response
  → Update UI
  → Show feedback
  → Enable next action
```

**Pattern 2: Auto-Load on Startup**
```
App starts
  → Load saved state
  → Then what? Show UI immediately or load data?
  → If load data: Show loading state
  → If data loads: Render UI
  → Then what? Auto-process or wait for user?
  → DECISION POINT: Conservative = wait for user
```

**Pattern 3: Cascade Effect**
```
Action X
  → Triggers Function A
  → Function A calls Function B
  → Function B makes API call
  → API call triggers Function C
  → Function C updates state
  → State update re-renders UI
  → Re-render triggers Function D
  → CASCADE! Did you plan for this?
```

### Red Flags in User Journeys

- ❌ **"Probably X happens"** → Verify, don't assume
- ❌ **"It should be obvious"** → It's not, document it
- ❌ **"Just a simple action"** → Check the cascade
- ❌ **Journey ends at first action** → Continue to natural end
- ❌ **No error cases considered** → What if it fails?

---

## Side Effects Identification

### What Are Side Effects?

**A side effect is any action that happens as a CONSEQUENCE of your code, not just the direct action itself.**

### Categories of Side Effects

**1. Function Call Cascades**
```javascript
// Your code:
this.loadDirectory()

// Hidden cascade:
loadDirectory()
  → renderFileList()
    → loadAllPreviews()  ← Did you know this happens?
      → API call for each file
        → Extract metadata  ← Expensive!
          → User sees: "Why is this slow?"
```

**2. State Changes**
```javascript
// Your code:
this.currentFiles = newFiles

// Hidden cascade:
currentFiles changes
  → Reactive watchers trigger
  → UI re-renders
  → Event listeners fire
  → Other components update
```

**3. Storage/Persistence**
```javascript
// Your code:
sessionStorage.setItem('key', 'value')

// Hidden consequence:
sessionStorage persists across refreshes
  → User refreshes page
  → Value still there
  → "Flush cache" doesn't clear it
  → User confused
```

**4. Event Listeners**
```javascript
// Your code:
document.addEventListener('click', handler)

// Hidden problem:
If not removed:
  → Memory leak
  → Duplicate handlers
  → Unexpected behavior
```

**5. Async Operations**
```javascript
// Your code:
await someAsyncOperation()

// Hidden race condition:
User clicks button
  → Async operation starts
  → User clicks again
  → Second operation starts
  → First completes, updates UI
  → Second completes, overwrites
  → Wrong state!
```

### Side Effects Checklist

For each function you write, check:

- [ ] **What functions does it call?**
  - Direct calls
  - Callback functions
  - Event handlers

- [ ] **What API calls does it make?**
  - How many?
  - Are they parallel or sequential?
  - What's the cost?

- [ ] **What data does it load?**
  - How much data?
  - From where? (API, local storage, cache)
  - Is it expensive?

- [ ] **What state does it change?**
  - Component state
  - Global state
  - DOM state
  - Browser storage

- [ ] **What UI changes does it trigger?**
  - Direct UI updates
  - Reactive re-renders
  - Animation/transitions
  - Scroll position changes

- [ ] **What computations does it perform?**
  - Cheap (< 10ms)?
  - Moderate (10-100ms)?
  - Expensive (> 100ms)?
  - Blocking UI?

- [ ] **What happens on error?**
  - Does it fail silently?
  - Does it show error to user?
  - Does it leave UI in bad state?

### Side Effects Template

```markdown
## Function: [functionName()]

### Direct Action
What the function is supposed to do

### Side Effects (Cascade)

#### Level 1: Immediate calls
- Calls `functionA()`
- Calls `functionB()`
- Makes API call to `/endpoint`

#### Level 2: Indirect calls
- `functionA()` calls `functionC()`
  - `functionC()` updates state
    - State update triggers re-render
      - Re-render calls `functionD()`

#### Level 3: Hidden consequences
- Re-render is expensive (100ms)
- API call loads 10MB of data
- User sees loading spinner unexpectedly

### Total Cost
- **Time**: X ms
- **Data**: X MB loaded
- **User experience**: [Description]

### Mitigation
- [ ] Debounce expensive operations
- [ ] Cache data when possible
- [ ] Show loading states
- [ ] Handle errors gracefully
```

---

## Technology Stack Selection

### Current Stack (Crate Project)

**Backend**:
- **Python 3.x** - Core language
- **FastAPI** - Web framework (async, fast, good docs)
- **Mutagen** - ID3 tag reading (pure Python, reliable)
- **librosa** - Audio analysis (considering migration to Essentia)

**Frontend**:
- **Vanilla JavaScript** - No framework (simple, fast, no build step)
- **HTML5 + CSS3** - Standard web technologies
- **Fetch API** - HTTP requests (built-in, no dependencies)

**Why This Stack?**
- ✅ **Simple**: No complex build tools
- ✅ **Fast**: Minimal dependencies
- ✅ **Reliable**: Mature technologies
- ✅ **Maintainable**: Easy to understand

### When to Choose Technologies

**Framework Selection Criteria**:

1. **Maturity**: Established with long-term support
2. **Documentation**: Excellent docs and examples
3. **Community**: Active community for help
4. **Performance**: Fast enough for use case
5. **Simplicity**: As simple as possible
6. **Dependencies**: Minimal dependency tree

**Red Flags**:
- ❌ "Shiny new framework" (immature, unstable)
- ❌ Requires complex build tooling (unless necessary)
- ❌ Poor documentation (will slow development)
- ❌ Abandoned/inactive (security risk)
- ❌ Massive dependencies (bloat, security surface)

### Library Selection Process

**1. Define Requirements**
```markdown
Need: Audio key detection
Requirements:
- Accurate (> 90% accuracy)
- Fast (< 1 second per track)
- Reliable (handles edge cases)
- Maintained (active development)
```

**2. Research Options**
```markdown
Option A: librosa
- Pros: Pure Python, easy install, good docs
- Cons: Slower, less accurate for key detection

Option B: Essentia
- Pros: Fast, accurate, industry-standard
- Cons: C++ dependency, harder install

Option C: Custom ML model
- Pros: Tailored to needs
- Cons: Requires training data, maintenance
```

**3. Evaluate Trade-offs**
```markdown
Factors:
- Accuracy: Essentia > Custom > librosa
- Speed: Essentia > Custom > librosa
- Ease of use: librosa > Custom > Essentia
- Maintenance: librosa > Essentia > Custom

Decision: Essentia (accuracy + speed > ease of use)
```

**4. Plan Migration**
```markdown
Migration Plan:
1. Create feature flag
2. Implement Essentia in parallel
3. Test with user's library
4. Compare results
5. Switch if better
6. Remove librosa code
7. Update docs
```

### Technology Decision Template

```markdown
## Technology Decision: [Choice]

### Requirements
- [Requirement 1]
- [Requirement 2]
- [Requirement 3]

### Options Evaluated

#### Option A: [Name]
**Description**: [What is it?]
**Pros**:
- [Pro 1]
- [Pro 2]
**Cons**:
- [Con 1]
- [Con 2]
**Performance**: [Metrics]
**Maturity**: [Status]
**Documentation**: [Quality]

#### Option B: [Name]
[Same structure]

### Decision
**Choice**: [Option X]
**Reasoning**: [Why?]
**Trade-offs**: [What we're accepting]
**Migration plan** (if changing): [Steps]

### Success Criteria
How will we know if this was the right choice?
- [Metric 1]
- [Metric 2]
```

---

## Implementation Best Practices

### Code Organization

**1. One Function, One Purpose**
```javascript
// ❌ BAD: Function does too many things
async loadDirectory() {
    const files = await api.listDirectory()
    this.currentFiles = files
    this.renderFileList()  // Side effect!
    this.loadPreviews()    // Side effect!
    this.analyzeContext()  // Side effect!
}

// ✅ GOOD: Function does ONE thing
async loadDirectory() {
    const files = await api.listDirectory()
    this.currentFiles = files
    // User explicitly triggers next steps
}
```

**2. Explicit Over Implicit**
```javascript
// ❌ BAD: Auto-triggers next action
renderFileList() {
    // Render files...
    this.loadAllPreviews()  // Surprise!
}

// ✅ GOOD: User triggers explicitly
renderFileList() {
    // Just render files
    // User clicks "Preview Rename" when ready
}
```

**3. Conservative Defaults**
```javascript
// ❌ BAD: Aggressive automation
async init() {
    const path = await getLastDirectory()
    await this.loadDirectory(path)      // Auto-load
    await this.loadAllPreviews()        // Auto-preview
    await this.analyzeWithAI()          // Expensive!
}

// ✅ GOOD: Conservative, user control
async init() {
    const path = await getLastDirectory()
    document.getElementById('path').value = path
    // User presses Enter to load
}
```

### Error Handling

**1. Always Use Try-Catch for Async**
```javascript
// ❌ BAD: No error handling
async loadFiles() {
    const result = await api.listDirectory(path)
    this.files = result.files
}

// ✅ GOOD: Graceful error handling
async loadFiles() {
    try {
        console.log('[LoadFiles] Starting...')
        const result = await api.listDirectory(path)
        this.files = result.files
        console.log('[LoadFiles] Success:', result.files.length, 'files')
    } catch (error) {
        console.error('[LoadFiles] Error:', error)
        this.ui.error('Failed to load files: ' + error.message)
        // Leave UI in safe state
        this.files = []
    }
}
```

**2. Fail Gracefully**
```javascript
// ❌ BAD: Crash on error
const metadata = await extractMetadata(file)
const bpm = metadata.bpm  // Crash if metadata null!

// ✅ GOOD: Defensive coding
const metadata = await extractMetadata(file)
const bpm = metadata?.bpm || null  // Safe fallback
```

### Logging

**1. Comprehensive Logging**
```javascript
// ✅ GOOD: Log everything significant
async loadDirectory(path) {
    console.log('[LoadDir] Starting load:', path)

    try {
        const result = await api.listDirectory(path)
        console.log('[LoadDir] API returned:', result.files.length, 'files')

        this.currentFiles = result.files
        console.log('[LoadDir] State updated')

        console.log('[LoadDir] Complete')
    } catch (error) {
        console.error('[LoadDir] Failed:', error)
        throw error
    }
}
```

**2. Tag Your Logs**
```javascript
// Use consistent prefixes for filtering:
console.log('[Task #84] Restored directory:', path)
console.log('[SmartDetect] Analyzing context...')
console.log('[Preview] Loading:', filename)
```

### State Management

**1. Clear State Transitions**
```javascript
// ✅ GOOD: Clear state management
async loadDirectory() {
    // Reset state for new directory
    this.currentFiles = []
    this.selectedFiles.clear()
    this.temporaryTemplate = null
    this.smartBannerDismissedForCurrentLoad = false

    // Load new data
    const result = await api.listDirectory(path)
    this.currentFiles = result.files
}
```

**2. Avoid State Persistence Surprises**
```javascript
// ❌ BAD: Persistent state causes confusion
onClick() {
    sessionStorage.setItem('dismissed', 'true')
    // User can't easily clear this!
}

// ✅ GOOD: In-memory state, clears on refresh
onClick() {
    this.dismissedForCurrentLoad = true
    // Automatically clears on page refresh
}
```

---

## Testing & Verification

### Test Case Structure

**For Every Feature, Define**:

1. **Happy Path**
   - Normal usage
   - Expected outcome
   - User sees success

2. **Edge Cases**
   - Empty data
   - Single item
   - Many items (1000+)
   - Special characters
   - Unicode/emoji

3. **Error Cases**
   - Network failure
   - Invalid input
   - Permission denied
   - File not found
   - Server error

4. **Side Effects**
   - Does it trigger unexpected actions?
   - Does it change other state?
   - Does it affect performance?

### Test Plan Template

```markdown
## Test Plan: [Feature Name]

### Setup
- Prerequisites
- Test data needed
- Environment configuration

### Test Case 1: [Name]
**Priority**: CRITICAL/HIGH/MEDIUM/LOW
**Estimated Time**: X minutes

#### Objective
What are we testing?

#### Steps
1. Step 1
2. Step 2
3. Step 3

#### Expected Results
✅ [Expected outcome 1]
✅ [Expected outcome 2]
✅ [Expected outcome 3]

#### Failure Criteria
❌ [What would indicate failure?]

#### Notes
Any additional context

### Test Case 2: [Name]
[Same structure]

### Quick Validation (5-minute version)
For rapid verification:
1. [Quick test 1]
2. [Quick test 2]
3. [Quick test 3]
```

### Verification Checklist

Before marking feature as complete:

- [ ] **Manual testing complete**
  - Happy path tested
  - Edge cases tested
  - Error cases tested

- [ ] **Console logs reviewed**
  - No unexpected errors
  - Actions logged correctly
  - Performance acceptable

- [ ] **User feedback received**
  - User tested the feature
  - User confirmed it works
  - No confusion or issues

- [ ] **Documentation updated**
  - current-status.md updated
  - Lessons learned documented (if needed)
  - Test plan created

- [ ] **Code reviewed**
  - Follows best practices
  - No obvious bugs
  - Proper error handling

---

## Documentation Requirements

### Files to Maintain in ./claude/

**1. current-status.md** (Update after EVERY session)
- Recent changes
- Feature status
- Testing status
- Known issues
- Next steps

**2. lessons-learned-[date]-[topic].md** (Create when iteration needed)
- What went wrong
- Why it went wrong
- What should have been done
- Key learnings

**3. best-practices.md** (Update when new patterns emerge)
- Framework for all features
- Checklists
- Templates
- Guidelines

**4. implementation-plan-[feature].md** (Create for medium/high risk features)
- Options considered
- Trade-offs
- Final decision
- Implementation steps

**5. test-plan-[feature].md** (Create for all testable features)
- Test cases
- Expected results
- Verification steps

**6. claude-coding-excellence-guide.md** (THIS FILE)
- Comprehensive guide
- Updated continuously
- Everything Claude needs to know

### Documentation Template Structure

**For Implementation Plans**:
```markdown
# Implementation Plan: [Feature Name]

**Date**: YYYY-MM-DD
**Task**: #XX
**Complexity**: Low/Medium/High

## Problem Statement
What are we solving?

## User Journey Analysis
[Complete journey with "Then what?"]

## Side Effects
[All side effects identified]

## Options

### Option A
[Full analysis]

### Option B
[Full analysis]

## Recommendation
[Choice with reasoning]

## Implementation Steps
1. [Step 1]
2. [Step 2]

## Test Plan
[How to verify]

## Rollback Plan
[How to undo if needed]
```

---

## Common Anti-Patterns to Avoid

### 1. The Assumption Trap

**❌ Anti-pattern**:
```javascript
// "I think users want auto-load"
async init() {
    const path = await getLastDirectory()
    await this.loadDirectory(path)  // Assumption!
}
```

**✅ Solution**:
```javascript
// Verify user intent
// After analysis: Users want path remembered, NOT auto-load
async init() {
    const path = await getLastDirectory()
    this.setDirectoryPath(path)  // Set path only
    // User explicitly triggers load
}
```

**How to Avoid**:
- Don't assume, verify
- Use AskUserQuestion when uncertain
- Map complete user journey
- Choose conservative default

### 2. The Cascade Trap

**❌ Anti-pattern**:
```javascript
// "This just loads files"
loadDirectory() {
    this.files = api.getFiles()
    this.render()  // Hidden: calls preview()
                   // Hidden: calls analyzeContext()
                   // Hidden: expensive operations!
}
```

**✅ Solution**:
```javascript
// One function, one purpose
loadDirectory() {
    this.files = api.getFiles()
    // User explicitly triggers next steps
}
```

**How to Avoid**:
- Identify ALL side effects upfront
- Ask "What does this function call?"
- Ask "What happens next?"
- Keep functions single-purpose

### 3. The Perfect Feature Trap

**❌ Anti-pattern**:
```
"Let me build the complete, perfect feature before showing user"
[2 days later]
User: "That's not what I wanted"
```

**✅ Solution**:
```
1. Build minimal version (30 minutes)
2. Show user, get feedback
3. Iterate if needed
4. Add next piece
```

**How to Avoid**:
- Build incrementally
- Get feedback early
- Don't wait for "perfect"
- User feedback > your assumptions

### 4. The Over-Engineering Trap

**❌ Anti-pattern**:
```javascript
// "Let me make this super flexible for future use"
class TemplateManager {
    constructor(config, validator, cache, logger) {
        // 200 lines of abstraction
        // Used in ONE place
    }
}
```

**✅ Solution**:
```javascript
// Solve current problem only
function applyTemplate(template, metadata) {
    // 10 lines of clear code
    return template.replace(/\{(\w+)\}/g, (_, key) => metadata[key] || '')
}
```

**How to Avoid**:
- Solve current problem only
- No hypothetical future requirements
- Three similar lines > premature abstraction
- YAGNI (You Aren't Gonna Need It)

### 5. The Silent Persistence Trap

**❌ Anti-pattern**:
```javascript
// Persists without user knowledge
onClick() {
    sessionStorage.setItem('dismissed', 'true')
    // User confused: "Why doesn't it show again?"
    // Cache flush doesn't help!
}
```

**✅ Solution**:
```javascript
// Temporary in-memory state
onClick() {
    this.dismissedForCurrentView = true
    // Clears on refresh (expected behavior)
}
```

**How to Avoid**:
- Avoid sessionStorage/localStorage unless necessary
- Use in-memory state by default
- If persisting, document clearly
- Match user mental model

### 6. The Skip Testing Trap

**❌ Anti-pattern**:
```
"It's a small change, I'll just commit it"
[Later: breaks production]
```

**✅ Solution**:
```
1. Test happy path
2. Test edge cases
3. Test error cases
4. Get user verification
5. Then commit
```

**How to Avoid**:
- Test before committing
- No "small change" exception
- User verification required
- Document what was tested

---

## Real-World Case Studies

### Case Study 1: Task #84 - Remember Last Directory

**Problem**: Feature required 3 iterations due to incomplete business logic analysis

**What Went Wrong**:
- Didn't map complete user journey
- Didn't identify side effects (load → render → preview → metadata)
- Made assumptions about user intent
- Each fix revealed new issues

**Timeline**:
1. **Iteration 1**: Set path + toast notification → FAILED (`this.ui.info()` doesn't exist)
2. **Iteration 2**: Fixed toast + auto-load with setTimeout → FAILED (triggered cascade, auto-previewed)
3. **Iteration 3**: Disabled auto-preview but kept auto-load → FAILED (still loaded metadata)
4. **Iteration 4**: Set path only, user triggers load → SUCCESS ✅

**Should Have Done**:
```markdown
BEFORE CODING:

1. Map Complete Journey:
   - User closes app
   - User reopens app
   - Path restored
   → Then what? Auto-load files?
   → Then what? Does render() run?
   → Then what? Does it auto-preview?
   → Then what? Does preview load metadata?
   → EXPENSIVE OPERATION on startup!

2. Identify Side Effects:
   - loadDirectory() → renderFileList() → loadAllPreviews() → expensive

3. Clarify Intent:
   - User wants: Path remembered
   - User doesn't want: Everything auto-loaded on startup

4. Choose Conservative Default:
   - Set path only
   - User explicitly triggers load
```

**Time Cost**: 3 iterations × 15 minutes = 45 minutes wasted
**Lesson**: 10 minutes of upfront analysis saves 45 minutes of iteration

**See**: `claude/lessons-learned-2026-01-30-task-84-remember-last-directory.md`

---

### Case Study 2: Task #105 - Smart Banner X Button

**Problem**: X button dismissed banner permanently until server restart

**Root Cause**:
- Used `sessionStorage` for dismissal
- `sessionStorage` persists across page refreshes
- User expectation: X = dismiss temporarily
- Reality: X = dismiss until server restart

**Analysis**:
```markdown
Current Behavior:
- X → sessionStorage.setItem('dismissed', 'true')
- Persists across refreshes
- "Flush cache" doesn't help
- Only clears on server restart

Expected Behavior:
- X = "Not now" (temporary dismissal)
- Banner reappears on refresh
- Banner reappears when loading different directory
```

**Solution**:
```javascript
// BEFORE: Persistent storage
sessionStorage.setItem(dismissalKey, 'true')

// AFTER: In-memory state
this.smartBannerDismissedForCurrentLoad = true
// Resets on refresh, resets on directory change
```

**Key Learning**: Match user mental model. X button = temporary dismissal in most UIs.

---

### Case Study 3: Task #98 - Button Visibility After Rename

**Problem**: After successful rename, Smart Track Detection banner stayed visible with clickable buttons

**Analysis**:
```markdown
User Journey:
1. User loads album
2. Banner suggests template
3. User clicks "Use This"
4. User renames files
5. Rename completes
   → Then what? Banner still shows same buttons
   → Problem: Action already taken, banner meaningless

Options:
A. Hide banner (action complete)
B. Disable buttons (show confirmation)
C. Keep as-is (confusing)

Decision: Option A (hide banner)
Reasoning: Action complete, banner no longer needed, reduces clutter
```

**Solution**:
```javascript
// After rename completes successfully
if (results.renamed > 0) {
    this.hideSmartSuggestion()
    this.smartBannerDismissedForCurrentLoad = true
    console.log('[Task #98] Banner hidden after successful rename')
}
```

**Key Learning**: When user completes the suggested action, remove the suggestion UI.

---

## Quick Reference

### Decision Trees

**Should I use sessionStorage/localStorage?**
```
Do I need data to persist across page refreshes?
├─ NO → Use in-memory state (this.property)
└─ YES
   ├─ Is this expected by user?
   │  ├─ YES → Document clearly, use localStorage
   │  └─ NO → Reconsider, probably use in-memory
   └─ Can user easily clear it?
      ├─ YES → OK to use
      └─ NO → Don't use, will cause confusion
```

**Should I auto-load/auto-preview/auto-anything?**
```
Is this action expensive (API call, computation)?
├─ YES
│  └─ Does user explicitly expect it on startup?
│     ├─ YES → OK to auto-load
│     └─ NO → Let user trigger explicitly
└─ NO (cheap)
   └─ Does it change user's context?
      ├─ YES → Let user trigger
      └─ NO → OK to auto-run
```

**Should I add a new dependency/library?**
```
Can I solve this with existing code?
├─ YES → Use existing code (avoid dependency)
└─ NO
   ├─ Is library mature and maintained?
   │  ├─ NO → Don't use
   │  └─ YES
   │     ├─ Does it have good documentation?
   │     │  ├─ NO → Don't use
   │     │  └─ YES
   │     │     ├─ Is it the best option for our needs?
   │     │     │  ├─ YES → OK to add
   │     │     │  └─ NO → Find better option
```

### Templates

**Feature Implementation**
```markdown
## Feature: [Name]

### Analysis Complete
- [x] User journey mapped
- [x] Side effects identified
- [x] User intent clarified
- [x] Options evaluated
- [x] Tests defined

### Implementation
[Steps taken]

### Verification
[How verified]

### Documentation Updated
- [x] current-status.md
- [x] Test plan created
- [x] Lessons learned (if iteration needed)
```

**Bug Fix**
```markdown
## Bug: [Description]

### Root Cause
[Why it happened]

### User Impact
[What user experienced]

### Fix
[What changed]

### Prevention
[How to avoid in future]

### Verification
[How verified fixed]
```

### Command Quick Reference

**Search for patterns**:
```bash
grep -n "pattern" file.js
grep -rn "pattern" directory/
```

**Find files**:
```bash
find . -name "*.js" -type f
```

**Check logs**:
```bash
# Browser console (F12)
# Look for [Tag] prefixes
```

**Git operations**:
```bash
git status
git diff
git log --oneline -10
```

---

## Continuous Improvement

This guide is a living document. After each feature or bug fix:

1. **Update if new pattern emerges**
2. **Add to anti-patterns if mistake repeated**
3. **Document new lessons learned**
4. **Refine templates based on experience**

---

## Summary

**Core Message**: Think first, code second. Spending 10 minutes on analysis saves 45 minutes on iteration.

**Key Practices**:
1. ✅ Complete user journey analysis before coding
2. ✅ Identify ALL side effects upfront
3. ✅ Choose conservative defaults (user control)
4. ✅ Build incrementally, test continuously
5. ✅ Document everything in ./claude/
6. ✅ Learn from every iteration

**When Uncertain**: Use AskUserQuestion. User feedback > assumptions.

**Remember**: The user wants to trust but needs to verify. Transparency and documentation build that trust.

---

**Next**: Read relevant lessons learned and current-status.md before starting any new work.
