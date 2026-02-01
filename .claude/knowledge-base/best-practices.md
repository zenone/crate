# Best Practices for Claude Code - Crate Batch Renamer

**Date**: 2026-01-30
**Purpose**: Framework and guidelines for Claude to implement features correctly the first time
**Status**: Living document - update as we learn

---

## Overview

This document contains the comprehensive framework that **MUST be applied to ALL future features**. It was created after Task #84 required 3 iterations due to incomplete business logic review.

**Core Principle**: Spending 5-10 minutes on upfront analysis saves 45+ minutes of iteration and rework.

---

## The Comprehensive Review Framework

Apply this framework to **EVERY** feature implementation, no exceptions.

### Phase 1: BEFORE Coding (CRITICAL)

#### 1.1: Map Complete User Journey

**What**: Write out the complete flow from user action to final result

**How**:
```
Step 1: User does X
Step 2: System responds with Y
Step 3: Then what happens?
Step 4: Then what happens?
Step 5: Continue until natural stopping point
```

**Example (Task #84)**:
```
1. User browses to directory X
2. User stops server
3. User restarts server
4. User opens web app
   → Then what? Auto-load files? Or just remember path?
5. If auto-load: System loads files
   → Then what? Auto-preview? Or wait for user?
6. If auto-preview: System generates previews
   → Then what? Load metadata? How expensive is this?
```

**Red Flags**:
- ❌ "I think the user wants..." (Don't assume)
- ❌ "Probably X happens next..." (Verify)
- ❌ "It should be obvious..." (It's not)

#### 1.2: Identify ALL Side Effects

**What**: For each system action, identify what else it triggers

**How**:
```
Action: functionName()
Side Effects:
  - Calls other functions: [list them]
  - Makes API calls: [list them]
  - Loads data: [what data? how much?]
  - Changes UI state: [what changes?]
  - Triggers events: [what events?]
  - Computation cost: [cheap/expensive?]
```

**Example (Task #84)**:
```
Action: loadDirectory()
Side Effects:
  - Calls renderFileList()
    → renderFileList() auto-calls loadAllPreviews() (line 886)
      → loadAllPreviews() makes API call for each file
        → API extracts metadata (expensive)
        → User sees: "Why is this happening on startup?"
```

**Red Flags**:
- ❌ "This function just loads the directory" (Check what ELSE it does)
- ❌ "It's a simple call" (Check the cascade)
- ❌ "No side effects" (Verify this is true)

#### 1.3: Clarify User Intent

**What**: Understand what the user actually wants vs what you assume

**Questions to Ask**:
- What problem is the user trying to solve?
- What's the expected behavior?
- What should happen on startup vs user action?
- Should this be automatic or explicit?
- What's the safe default?

**When Uncertain**:
- ✅ Use AskUserQuestion tool
- ✅ Present 2-3 options with trade-offs
- ✅ Let user decide
- ❌ Don't guess
- ❌ Don't assume

**Example (Task #84)**:
```
Question: "Should the app auto-load files on startup, or just remember the path?"

Option 1: Auto-load files (continue work)
  Pros: User picks up where they left off
  Cons: Wastes computation if user doesn't want those files, triggers cascade

Option 2: Remember path only (fresh start)
  Pros: User has explicit control, no wasted computation
  Cons: One extra Enter keypress required

Option 3: User preference in settings
  Pros: Flexible
  Cons: Adds complexity for rare feature

Recommendation: Option 2 (conservative, user control)
```

#### 1.4: Choose Conservative Defaults

**What**: When in doubt, give user explicit control

**Principles**:
- ✅ Conservative > Aggressive
- ✅ Explicit > Automatic
- ✅ User control > System automation
- ✅ Cheap operations > Expensive operations on startup

**Examples**:
- ✅ Remember path → User presses Enter to load (conservative)
- ❌ Auto-load files on startup (aggressive)
- ✅ User clicks "Preview Rename" → Previews generate (explicit)
- ❌ Auto-generate previews when files load (automatic)

#### 1.5: Document Trade-offs

**What**: Write down pros/cons of each approach

**Template**:
```
## Implementation Options

### Option 1: [Name]
**Approach**: [Description]
**Pros**:
- Pro 1
- Pro 2
**Cons**:
- Con 1
- Con 2
**Side Effects**: [List]
**Recommendation**: [Yes/No and why]

### Option 2: [Name]
[Same structure]

### Option 3: [Name]
[Same structure]

## Final Decision
[Which option and why]
```

#### 1.6: Write Expected Behavior

**What**: Define exactly what should happen in each scenario

**Template**:
```
## Expected Behavior

### Scenario 1: Normal Flow
Given: [Initial state]
When: [User action]
Then: [System response]
And: [Next action]
And: [Next action]

### Scenario 2: Edge Case
Given: [Initial state]
When: [User action]
Then: [System response]

### Scenario 3: Error Case
Given: [Initial state]
When: [Error occurs]
Then: [System response]
```

---

### Phase 2: DURING Coding

#### 2.1: Implement Incrementally

**What**: Code smallest viable piece, test it, then continue

**Approach**:
1. Write minimal code for Step 1
2. Test Step 1
3. If works → Continue to Step 2
4. If fails → Fix before continuing

**Red Flags**:
- ❌ Implementing entire feature at once
- ❌ "I'll test it all at the end"
- ❌ Writing code without testing intermediate steps

#### 2.2: Add Comprehensive Logging

**What**: Console.log every significant action

**Why**:
- Makes debugging trivial
- User can verify behavior
- Shows exactly what's happening
- Helps identify unexpected side effects

**Example**:
```javascript
console.log('[Task #84] Fetching initial directory...');
const initialDir = await this.api.getInitialDirectory();
console.log('[Task #84] Received:', initialDir);

if (initialDir.path) {
    console.log('[Task #84] Setting directory path:', initialDir.path);
    document.getElementById('directory-path').value = initialDir.path;
    console.log('[Task #84] Path set. User can press Enter to load files.');
}
```

#### 2.3: Handle Errors Gracefully

**What**: Every API call, every async operation needs try/catch

**Template**:
```javascript
try {
    console.log('[Feature] Starting operation...');
    const result = await riskyOperation();
    console.log('[Feature] Success:', result);
} catch (error) {
    console.error('[Feature] Error:', error);
    // Decide: Show error to user? Fail silently? Fallback?
}
```

#### 2.4: Avoid Cascading Side Effects

**What**: Each function should do ONE thing

**Red Flags**:
- ❌ `loadDirectory()` also generates previews
- ❌ `renderFileList()` also makes API calls
- ❌ `init()` loads everything automatically

**Better**:
- ✅ `loadDirectory()` loads files only
- ✅ User clicks "Preview" → Then previews generate
- ✅ `init()` sets up UI, doesn't auto-load data

---

### Phase 3: AFTER Coding

#### 3.1: Test All Scenarios

**What**: Don't just test happy path

**Test Cases**:
- ✅ Happy path (normal flow)
- ✅ Edge cases (empty directory, single file, etc.)
- ✅ Error cases (directory deleted, network error, etc.)
- ✅ Side effects (does it trigger anything unexpected?)
- ✅ Startup behavior (what happens on restart?)

#### 3.2: Get User Feedback Early

**What**: Don't wait until "finished" to show user

**Approach**:
1. Implement minimal version
2. Get user feedback
3. Iterate if needed
4. Add next piece

**Red Flags**:
- ❌ "Let me finish the whole feature first"
- ❌ "I'll show it when it's perfect"
- ❌ Building for days without user input

#### 3.3: Document Lessons Learned

**What**: If iteration was needed, document why

**Template**: See `lessons-learned-2026-01-30-task-84-remember-last-directory.md`

**Key Questions**:
- What went wrong?
- Why did it need iteration?
- What should I have done differently?
- What will I do next time?

---

## Feature Implementation Checklist

Use this checklist for **EVERY** feature:

### BEFORE Coding
- [ ] Complete user journey mapped from start to finish
- [ ] All side effects identified (function calls, API calls, data loads)
- [ ] User intent clarified (or AskUserQuestion used)
- [ ] Conservative default chosen (user control > automation)
- [ ] Trade-offs documented (pros/cons of each approach)
- [ ] Expected behavior written (Given/When/Then format)
- [ ] Test cases defined (happy path + edge cases + errors)

### DURING Coding
- [ ] Incremental implementation (test each step)
- [ ] Comprehensive logging added (console.log every action)
- [ ] Error handling added (try/catch for async ops)
- [ ] Side effects avoided (each function does ONE thing)

### AFTER Coding
- [ ] All scenarios tested (happy + edge + error)
- [ ] User feedback received (show early, iterate if needed)
- [ ] Lessons learned documented (if iteration needed)
- [ ] Current status updated (`claude/current-status.md`)

### DEPLOYMENT
- [ ] Test plan created (for user verification)
- [ ] Documentation updated (README, current-status, etc.)
- [ ] Feature flag available (if risky feature)
- [ ] Rollback plan defined (how to disable if issues)

**If ANY checkbox is unchecked → STOP and complete it before continuing**

---

## Common Anti-Patterns to Avoid

### 1. The Assumption Trap
❌ "I think the user wants X"
✅ "Let me verify what the user wants"

### 2. The Cascade Trap
❌ "This function just does X" (but triggers Y, Z, and W)
✅ "This function does X, which calls Y, which calls Z"

### 3. The Perfect Feature Trap
❌ "Let me build the whole thing perfectly before showing user"
✅ "Let me build minimal version and get feedback"

### 4. The Aggressive Automation Trap
❌ "Auto-load everything to save user clicks"
✅ "Let user explicitly control when things happen"

### 5. The No Logging Trap
❌ "I don't need logs, the code is simple"
✅ "Comprehensive logging makes debugging trivial"

### 6. The Skip Testing Trap
❌ "It's a small change, I'll just commit it"
✅ "Test happy path + edge cases before committing"

---

## Real-World Example: Task #84

See `claude/lessons-learned-2026-01-30-task-84-remember-last-directory.md` for detailed analysis.

**Summary**: Task #84 required 3 iterations because I didn't map the user journey upfront. If I had followed this framework:

**Phase 1 (BEFORE)**: Map journey → Identify side effects → Choose conservative default
**Result**: Would have chosen "set path only" immediately
**Time Saved**: 45 minutes of iteration

---

## When to Use AskUserQuestion

Use AskUserQuestion when:
- ✅ User intent is unclear
- ✅ Multiple valid approaches exist
- ✅ Trade-offs are not obvious
- ✅ Feature affects core workflow
- ✅ Default behavior is ambiguous

Don't use AskUserQuestion when:
- ❌ Answer is obvious from context
- ❌ Conservative default is clear
- ❌ You're asking to avoid thinking
- ❌ Question is too technical for user

---

## Feature Risk Assessment

Before implementing, assess risk:

### Low Risk (Quick implementation OK)
- Single function change
- No side effects
- Easy to test
- Easy to rollback

### Medium Risk (Use framework)
- Multiple function changes
- Some side effects
- Affects user workflow
- Requires testing

### High Risk (MUST use framework)
- Changes core functionality
- Many side effects
- Affects startup/initialization
- Hard to rollback
- User data at risk

**Task #84 was HIGH RISK** (affects startup, has side effects) but I treated it as LOW RISK. That's why it needed 3 iterations.

---

## Documentation Requirements

### For Every Feature

1. **Implementation Plan**: `claude/implementation-plan-[feature-name].md`
   - Options considered
   - Trade-offs
   - Final decision
   - Test plan

2. **Lessons Learned**: `claude/lessons-learned-[date]-[feature-name].md` (if iteration needed)
   - What went wrong
   - Why it needed iteration
   - What to do differently

3. **Current Status**: Update `claude/current-status.md`
   - Add to "Recent Changes"
   - Update "Files Modified"
   - Update "Testing Status"

---

## Success Metrics

**A feature implementation is successful when**:

✅ Works correctly on first try (no iteration needed)
✅ User says "Perfect!" or "That worked!"
✅ No unexpected side effects
✅ No wasted computation
✅ User has explicit control
✅ Comprehensive logging shows exactly what's happening
✅ All test cases pass
✅ Documentation complete

**A feature implementation needs improvement when**:

❌ Requires iteration (2+ attempts)
❌ User says "Think the proper business logic through"
❌ User discovers side effects I missed
❌ User has to explain what they want multiple times
❌ Incomplete analysis upfront

---

## Claude-Specific Guidelines

### How to Apply This Framework

1. **Read this document BEFORE implementing any feature**
2. **Complete Phase 1 (BEFORE) checklist BEFORE writing code**
3. **If ANY uncertainty exists → Use AskUserQuestion**
4. **Document everything in `claude/` directory**
5. **Update this document as we learn new patterns**

### When User Requests Feature

1. Read feature request
2. Open this file (best-practices.md)
3. Complete BEFORE phase checklist
4. If ready → Code incrementally
5. If uncertain → AskUserQuestion
6. Test thoroughly
7. Get user feedback
8. Document lessons learned

### Key Questions to Always Ask

Before coding ANY feature:
1. "What's the complete user journey?"
2. "What are ALL the side effects?"
3. "What's the user's intent?"
4. "What's the conservative default?"
5. "What could go wrong?"
6. "How will I test this?"

---

## Related Documents

- `claude/current-status.md` - Current project state
- `claude/lessons-learned-*.md` - Historical lessons learned
- `claude/implementation-plan-*.md` - Feature implementation plans
- `claude/test-plan-*.md` - Test plans for features

---

## Version History

- **v1.0** (2026-01-30): Initial version created after Task #84 lessons learned

---

## Tags

`#best-practices` `#framework` `#business-logic` `#user-journey` `#side-effects` `#quality`
