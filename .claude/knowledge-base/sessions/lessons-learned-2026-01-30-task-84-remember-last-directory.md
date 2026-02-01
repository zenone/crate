# Lessons Learned: Task #84 - Remember Last Directory

**Date**: 2026-01-30
**Task**: #84 - Remember Last Directory with intelligent fallback
**Result**: ✅ SUCCESS (after 3 iterations)
**Severity**: CRITICAL LEARNING

---

## Summary

Task #84 (Remember Last Directory) required **3 iterations** to implement correctly because the initial approach didn't map the complete user journey before coding. Each fix revealed new business logic issues that should have been identified upfront.

---

## The Problem

**Initial Implementation**: Auto-load last directory on startup
**User Feedback After Each Iteration**:
1. "Think the proper business logic through on this"
2. "It started auto previewing as soon as the webpage loaded... should the business logic not auto preview?"
3. "Perhaps when I restart the server and the webpage first comes up, it doesn't show the files in the pre-saved directory? Maybe wait until I select a directory?"

---

## What Went Wrong

### Iteration 1: Basic Implementation (FAILED)
**What I Did**: Set directory path + called `this.ui.info()` for toast notification
**Issue**: `this.ui.info()` doesn't exist - broke the feature entirely
**User Feedback**: Screenshot showing console error

### Iteration 2: Deferred Auto-Load (FAILED)
**What I Did**:
- Fixed toast notification error
- Set directory path
- Used `setTimeout(100ms)` to auto-load directory files

**Issue**: This triggered a cascade:
- Auto-loaded files → Triggered `renderFileList()` → Auto-generated previews → Loaded metadata
- User saw: "It started auto previewing as soon as the webpage loaded"
- Too aggressive for startup behavior

**User Feedback**: "Should the business logic not auto preview? Think this through"

### Iteration 3: Disabled Auto-Preview (FAILED)
**What I Did**:
- Kept directory path + auto-load files
- Disabled auto-preview in `renderFileList()` by commenting out line 886

**Issue**: Still auto-loaded files (metadata extraction, wasted computation)
**User Feedback**: "Perhaps... doesn't show the files... Maybe wait until I select a directory?"

### Iteration 4: FINAL SOLUTION (SUCCESS ✅)
**What I Did**: Set path ONLY, don't auto-load anything
```javascript
// Task #84: Remember Last Directory - Option 2 (Set Path Only)
const initialDir = await this.api.getInitialDirectory();
if (initialDir.path) {
    document.getElementById('directory-path').value = initialDir.path;
    console.log('[Task #84] Restored last directory path: ${initialDir.path}');
    console.log('[Task #84] Press Enter or click Browse to load files');

    // DON'T auto-load - let user explicitly trigger load
}
```

**User Feedback**: "PERFECT! Tests worked!"

---

## Root Cause Analysis

### Why 3 Iterations Were Needed

**I didn't ask "Then what?" after each step**:
1. ❌ Set directory path → Then what? (Should it load files?)
2. ❌ Load files → Then what? (Does renderFileList() auto-preview?)
3. ❌ Preview → Then what? (Does preview load metadata?)
4. ❌ What's the user's intent? (Continue work vs fresh start?)

**I made assumptions instead of mapping the journey**:
- Assumed: "User wants to continue where they left off"
- Reality: "User wants path remembered but wants explicit control"
- Assumed: "Auto-load is helpful"
- Reality: "Auto-load wastes computation if user doesn't want it"

---

## Side Effects Not Considered

Each action has side effects I should have mapped:

```
Set Path (✓ OK)
  ↓
Load Directory (TOO AGGRESSIVE)
  ↓
renderFileList() called
  ↓
Auto-preview triggered (line 886) (TOO AGGRESSIVE)
  ↓
Metadata extraction for all files (EXPENSIVE)
  ↓
User sees: "Why is it doing all this on startup?"
```

---

## What I Should Have Done

### BEFORE Coding

1. **Map Complete User Journey**:
   - User closes app
   - Server restarts
   - User opens app
   - **Then what?** → Path remembered but nothing loaded
   - User presses Enter or clicks Browse
   - **Then what?** → Files load
   - User clicks "Preview Rename"
   - **Then what?** → Previews generate

2. **Identify All Side Effects**:
   - Setting path → No side effects ✅
   - Loading directory → Calls renderFileList() → Auto-preview? ⚠️
   - Preview → Loads metadata for all files → Expensive ⚠️

3. **Clarify User Intent**:
   - Does user want to continue work? (Unknown)
   - Does user want fresh start? (Unknown)
   - Which is safer default? (Fresh start - user has control)

4. **Choose Conservative Default**:
   - Set path only (safe)
   - User explicitly triggers everything else (safe)
   - No wasted computation (safe)
   - User has full control (safe)

---

## Best Practices Learned

### 1. Map the Complete User Journey First

**Before writing ANY code, write out**:
```
Action 1 → Result → Then what?
Action 2 → Result → Then what?
Action 3 → Result → Then what?
...until natural stopping point
```

### 2. Identify All Side Effects

**For each action, check**:
- Does it trigger other functions?
- Does it load data?
- Does it make API calls?
- Does it change UI state?
- Does it waste computation?

### 3. Ask User About Intent (When Unclear)

**Use AskUserQuestion for**:
- "Should startup auto-load files or just remember path?"
- "Should loading files auto-generate previews?"
- "What's the expected startup behavior?"

### 4. Choose Conservative Defaults

**When in doubt**:
- ✅ Give user explicit control
- ✅ Minimize automatic actions
- ✅ Avoid expensive operations on startup
- ✅ Let user trigger when ready

### 5. Test Each Assumption

**Don't assume**:
- "User wants to continue work" → Test this
- "Auto-load is helpful" → Test this
- "Previews should auto-generate" → Test this

---

## Framework for Future Features

### BEFORE Phase (Critical)

#### Step 1: Map User Journey
Write complete flow from start to finish:
```
1. User action X
2. System does Y
3. Then what happens?
4. Then what happens?
5. Continue until natural end
```

#### Step 2: Identify Side Effects
For each system action:
- What functions does it call?
- What data does it load?
- What API calls does it make?
- What computations does it trigger?

#### Step 3: Clarify Intent
If ANY uncertainty:
- Use AskUserQuestion
- Don't assume
- Don't guess

#### Step 4: Choose Default Behavior
- Conservative > Aggressive
- Explicit > Automatic
- User control > System automation

### DURING Phase

#### Step 5: Implement Incrementally
- Code smallest viable piece
- Test it
- Then add next piece

#### Step 6: Log Everything
- Console.log each step
- Makes debugging easy
- User can verify behavior

### AFTER Phase

#### Step 7: Get User Feedback
- Does it match expectations?
- Any unexpected behavior?
- Any side effects?

#### Step 8: Iterate if Needed
- Fix issues immediately
- Don't accumulate tech debt

---

## Concrete Example: Task #84

### What I Should Have Written BEFORE Coding

```
USER JOURNEY:
1. User browses to Alabama Shakes directory
2. User stops server
3. User restarts server
4. User opens web app
   → Then what? Should directory auto-load files?
   → OR should it just remember the PATH?

SIDE EFFECTS:
- Set path: No side effects ✅
- Load directory: Calls renderFileList()
  - renderFileList() line 886: Auto-generates previews
  - Previews: Load metadata for ALL files
  - Expensive on startup? YES ⚠️

USER INTENT:
- Continue work? Unknown
- Fresh start? Unknown
- Which is safer? Fresh start (user controls everything)

DECISION:
Option 1: Auto-load everything (AGGRESSIVE)
Option 2: Set path only (CONSERVATIVE) ← Choose this
Option 3: Ask user preference (TOO COMPLEX for this feature)
```

**If I had done this analysis**, I would have chosen Option 2 immediately and saved 3 iterations.

---

## Impact

**Time Cost**: 3 iterations × 15 minutes = 45 minutes wasted
**User Friction**: User had to provide feedback 3 times
**Trust Impact**: User said "I WANT TO TRUST BUT ALSO NEED TO VERIFY"

**Lesson**: Spending 5-10 minutes on upfront analysis saves 45+ minutes of iteration.

---

## Action Items for Future

### For Claude (Me)

1. ✅ **ALWAYS map complete user journey BEFORE coding**
2. ✅ **ALWAYS identify side effects BEFORE coding**
3. ✅ **Use AskUserQuestion when intent unclear**
4. ✅ **Choose conservative defaults**
5. ✅ **Test assumptions before implementing**

### For This Project

1. ✅ Document this lesson learned (this file)
2. ✅ Add to best-practices.md framework
3. ✅ Apply framework to ALL future features
4. ✅ Update current-status.md with lessons learned

---

## Success Criteria for Future Features

**A feature implementation is ready to code when**:

✅ Complete user journey mapped from start to finish
✅ All side effects identified
✅ User intent clarified (or conservative default chosen)
✅ Trade-offs documented
✅ Expected behavior defined
✅ Test cases written

**If ANY of these are missing → STOP and complete them first**

---

## Related Documents

- `claude/best-practices.md` - Framework applied to all future features
- `claude/current-status.md` - Updated with Task #84 completion
- `implementation-plan-remember-last-directory.md` - Original implementation plan

---

## Tags

`#lessons-learned` `#business-logic` `#user-journey` `#side-effects` `#iteration` `#task-84`
