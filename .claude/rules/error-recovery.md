# Error Recovery Patterns

What to do when AI goes off track mid-task.

---

## Recognize the Signs

**AI is off track when:**
- Output doesn't match what you asked for
- Code has obvious errors you already mentioned
- Same mistake repeated after correction
- Scope creep (doing things you didn't ask for)
- Confident but wrong answers
- Circular reasoning or stuck in a loop

## Correction Strategies

### Level 1: Clarify (Quick Fix)
For minor misunderstandings:

```
"Stop. That's not what I meant. Let me clarify:
- I want X, not Y
- The constraint is Z
- Please redo just the [specific part]"
```

### Level 2: Reset Context (Medium Fix)
When clarification isn't working:

```
"Let's step back. Forget the last few messages.

Here's what I need, fresh:
1. [Clear requirement]
2. [Clear constraint]
3. [Clear acceptance criteria]

Start over from scratch."
```

### Level 3: New Session (Hard Reset)
When context is too polluted:

1. Update `.claude/state/current-state.md` with what went wrong
2. Exit session
3. Start fresh session
4. AI will load clean state from files

### Level 4: Manual Override (Escape Hatch)
When AI keeps failing:

```
"Stop trying to do X. I'll do it manually.
Instead, just do Y."
```

Sometimes human intervention is faster than debugging AI behavior.

---

## Common Failure Modes

### 1. Hallucinating APIs/Functions
**Symptom**: AI uses functions that don't exist
**Fix**: "Check the actual codebase. Don't assume any functions exist without reading them first."

### 2. Scope Creep
**Symptom**: AI "improves" things you didn't ask to change
**Fix**: "Only change what I specifically asked. Don't refactor, clean up, or 'improve' anything else."

### 3. Ignoring Constraints
**Symptom**: AI ignores stated requirements
**Fix**: "You missed this constraint: [X]. Stop and re-read my requirements."

### 4. Stuck in Loop
**Symptom**: Same error/approach repeated
**Fix**: Start new session. The context is polluted.

### 5. Over-Confident Wrong Answer
**Symptom**: AI insists on incorrect approach
**Fix**: "Show me where in the code/docs that's true." (Force verification)

---

## Prevention Strategies

### Be Specific Upfront
❌ "Add authentication"
✅ "Add JWT auth to POST /login endpoint. Use bcrypt for passwords. Return token in response body."

### State Constraints Explicitly
```
CONSTRAINTS:
- Do NOT modify any files except auth.py
- Do NOT add new dependencies
- Do NOT change existing function signatures
```

### Request Verification
```
"Before implementing, tell me:
1. Which files you'll modify
2. What approach you'll take
3. What could go wrong"
```

### Checkpoint Frequently
For complex tasks, request approval after each step rather than at the end.

---

## Recovery Checklist

When things go wrong:

- [ ] Identify what went wrong (output vs expectation)
- [ ] Check if state files need updating
- [ ] Decide: clarify, reset context, or new session?
- [ ] If code was changed: check git diff, consider reverting
- [ ] Document the failure in lessons-learned.md (prevent repeat)

---

## When to Give Up on AI

Use manual approach when:
- AI has failed 3+ times on same task
- Task requires context AI doesn't have (proprietary knowledge)
- Task is faster to do manually than to explain
- Security-critical code you don't trust AI to write

**No shame in manual work.** AI is a tool, not a replacement.
