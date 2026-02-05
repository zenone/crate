# Session Handoff Patterns

How to efficiently resume work across sessions.

---

## Why Sessions End

- Context window fills up (75-80%)
- Natural break (end of day, lunch)
- Conversation compression
- Crash or timeout
- Switching machines

## The Handoff Protocol

### Before Ending Session

1. **Update state file**:
```markdown
# .claude/state/current-state.md

## Last Session: 2026-02-05 14:00

### What was done:
- Implemented user authentication (auth.py)
- Added tests for login endpoint
- Fixed bug in token validation

### What's next:
- Add password reset flow
- Write integration tests
- Update README with auth docs

### Current blockers:
- None

### Files modified this session:
- core/auth.py (new)
- api/routes.py (modified)
- tests/test_auth.py (new)
```

2. **Commit work in progress**:
```bash
git add -A
git commit -m "WIP: Auth implementation (session checkpoint)"
```

3. **Note any gotchas** in `lessons-learned.md`:
```markdown
## [2026-02-05] JWT Token Format
The frontend expects token in { token: "..." } not { access_token: "..." }
```

### Starting New Session

AI should be instructed to:
1. Read `.claude/state/current-state.md` (where we left off)
2. Read `.claude/knowledge-base/lessons-learned.md` (recent gotchas)
3. Check `git log -5` (recent commits)
4. Ask for clarification if state is unclear

### First Prompt in New Session

Template:
```
Read .claude/state/current-state.md and continue where we left off.

Quick context refresh:
- Project: [name]
- Goal: [current goal]
- Priority: [what to work on first]

Start by telling me what you understand the current state to be.
```

---

## Context Refresh Techniques

### For Short Breaks (<1 hour)
Context likely intact. Just continue.

### For Medium Breaks (1-24 hours)
```
"Check .claude/state/current-state.md and summarize where we left off before continuing."
```

### For Long Breaks (>24 hours)
```
"Read these files in order, then summarize your understanding:
1. .claude/state/current-state.md
2. .claude/knowledge-base/lessons-learned.md
3. .claude/knowledge-base/tech-stack-decisions.md

What's the current project state and what should we work on next?"
```

### For Different Machine
If switching between machines:
```
"I'm now on [machine name]. The repo is synced. 
Read .claude/state/current-state.md and confirm you see the latest state."
```

---

## State File Best Practices

### Keep It Current
Update after every meaningful change, not just at session end.

### Keep It Actionable
Focus on "what's next" not just "what was done".

### Keep It Honest
Include blockers, uncertainties, and things that didn't work.

### Keep It Scannable
Use bullet points, headers, and short sentences.

---

## Anti-Patterns

❌ **No state update**: "I'll remember" (you won't, AI won't)

❌ **Vague state**: "Made progress on auth" (useless)

❌ **Outdated state**: Last updated 3 days ago (confusing)

❌ **Repeating context**: Manually re-explaining everything each session

---

## Emergency Recovery

If state file is missing or corrupted:

```
"I don't have recent context. Help me reconstruct:
1. Run: git log --oneline -10
2. Run: git diff HEAD~5 --stat
3. Read: README.md
4. List: files modified in last 24 hours

Then tell me what you think we were working on."
```

---

## Cross-Machine Handoff

When work moves between machines:

1. **Commit and push** on source machine:
```bash
git add -A
git commit -m "WIP: [description] (handoff to [target machine])"
git push
```

2. **Pull** on target machine:
```bash
git pull
```

3. **Verify state** matches:
```bash
cat .claude/state/current-state.md
git log -3
```

4. **Continue** with new session on target machine.
