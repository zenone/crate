# Human Checkpoints

## The "Trust But Verify" Principle

AI should do the work, but humans verify critical points.

**Pattern**: Show your work → Human approves → Execute

## When to Pause for Human Verification

### Always Pause Before:
- **Pushing to remote** (especially main/production branches)
- **Destructive operations** (delete, drop, remove)
- **External communication** (emails, API calls to production)
- **Security-sensitive changes** (auth, permissions, secrets)
- **Large refactors** (>20 files or >500 lines)
- **Dependency upgrades** (major versions)

### Checkpoint Format

When reaching a checkpoint, provide:

```markdown
## 🔍 Human Verification Checkpoint

**What I'm about to do**: [action]

**What I've done so far**:
- [x] Task 1
- [x] Task 2
- [x] Task 3

**Risks**:
- [risk 1]
- [risk 2]

**Commands to verify yourself**:
```bash
# Run tests
pytest tests/ -v

# Check diff
git diff --stat

# Manual test
python -m app --dry-run
```

**To proceed**: Reply "go" or "proceed"
**To abort**: Reply "stop" or provide alternative instructions
```

## Pre-Push Verification Ritual

Before `git push`, always:

```markdown
## Pre-Push Checklist

**Verification commands run**:
- [ ] `pytest tests/ -v` → All passed
- [ ] `ruff check .` → No errors
- [ ] `mypy src/` → No type errors

**Manual testing**:
- [ ] App starts: `python -m app`
- [ ] Core feature works: [specific test]
- [ ] No obvious regressions

**Human verified**:
- [ ] Reviewed diff: `git diff main`
- [ ] Commit messages are clear
- [ ] No secrets in code: `git diff main | grep -i "password\|secret\|key"`

Ready to push? Reply "push" to proceed.
```

## Task Visibility

For complex tasks, show all sub-tasks upfront:

```markdown
## Task Breakdown

**Original request**: [user's request]

**I will do the following**:
1. [ ] [Task 1] - [estimated risk: low/medium/high]
2. [ ] [Task 2] - [estimated risk]
3. [ ] [Task 3] - [estimated risk]
4. [ ] [Task 4] - [estimated risk]

**Checkpoints**:
- After task 2: Human review of [specific thing]
- After task 4: Final verification before push

**Proceed with task 1?**
```

## Recoverable vs Irrecoverable

| Action | Recoverable? | Checkpoint Required? |
|--------|--------------|---------------------|
| Edit local file | ✅ (git checkout) | No |
| Delete local file | ⚠️ (git checkout if tracked) | Recommend |
| Git commit | ✅ (git reset) | No |
| Git push | ⚠️ (force push, messy) | **Yes** |
| Delete remote branch | ⚠️ (can recreate) | **Yes** |
| Force push to main | ❌ (others may have pulled) | **ALWAYS** |
| Send email | ❌ | **ALWAYS** |
| API call to production | ❌ | **ALWAYS** |
| Database migration | ⚠️ (depends) | **Yes** |

## Checkpoint Responses

Human can respond:
- **"go"** / **"proceed"** / **"yes"** → Continue
- **"stop"** / **"abort"** / **"no"** → Halt and await instructions
- **"show me X first"** → Provide more info before deciding
- **"do Y instead"** → Change approach

## Anti-Pattern: Silent Execution

❌ **Don't do this**:
```
[AI completes 15 tasks silently]
[AI pushes to GitHub]
"Done! I pushed everything."
```

✅ **Do this instead**:
```
[AI completes task 1-5]
"Checkpoint: First phase complete. Here's what I did: [summary]
Ready for phase 2? This includes [risky action]. Reply 'go' to proceed."
```
