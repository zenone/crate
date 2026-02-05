# Project Template — OpenClaw Guidance

For OpenClaw (or any tool-using agent) working on repos created from this template.

## Prime Directive
Prefer actions over advice: read files, produce minimal diffs, run tests, report results.

## Session Startup

### 1. Read (in order)
1. `CLAUDE.md` — coding contract (most important)
2. `.claude/state/current-state.md` — current focus
3. `.claude/knowledge-base/lessons-learned.md` — gotchas
4. `.claude/knowledge-base/tech-stack-decisions.md` — why we chose X
5. `PROJECT.md` — project-specific context (if it exists)

### 2. Bootstrap (if new project)
If `PROJECT.md` doesn't exist, this is a fresh project:
1. Create `PROJECT.md` from `docs/PROJECT.md.template`
2. Fill in project details based on task/requirements
3. If stack unknown, create `docs/STACK_DECISION.md` from template

### 3. Check Available Skills
Scan `<available_skills>` in your system prompt. If a skill matches the task, load its `SKILL.md` before proceeding.

### 4. Decide Mode
- **Investigation**: Unclear requirements → propose plan first
- **Implementation**: Clear requirements → execute with verification

## Execution Rules

### Small Chunks
- One task at a time
- Run tests between changes
- Commit frequently with descriptive messages

### Verification First
Before changing anything:
```bash
# Find the test command
make test || npm test || pytest
```

### Minimal Diffs
- Change only what's needed
- No drive-by refactors
- If tempted to "clean up" nearby code, note it for later

### Destructive Actions
**Ask first** before:
- `rm` (prefer `trash`)
- Database migrations
- Mass renames
- Large rewrites
- Anything irreversible

## Context Management

### Update State
After meaningful progress:
```bash
# Update current-state.md
echo "## $(date +%Y-%m-%d %H:%M)" >> .claude/state/current-state.md
echo "- Completed: ..." >> .claude/state/current-state.md
```

### Session Handoff
If stopping mid-task, record:
1. What was attempted
2. What worked / didn't work
3. Next steps

## Deliverable Format

Every response should include:

```
## Summary
- [1-3 bullets of what was done]

## Files Changed
- `path/to/file.py` — description

## How to Test
```bash
make test  # or specific command
```

## Risks / Edge Cases
- [If any]
```

## OpenClaw-Specific Features

### Spawn Sub-Agents
For research-heavy tasks, use `sessions_spawn`:
```
Task: "Research JWT best practices for Python and summarize findings"
```

### Cron for Reminders
Use `cron` tool for delayed notifications:
```
Remind me to review the PR in 30 minutes
```

### Cross-Session State
If working across multiple sessions, check/update:
- Memory files (`memory/*.md`)
- `MEMORY.md` (if main session)

## Quick Commands

```bash
# Verify everything works
make verify || ./scripts/verify.sh

# Check machine prerequisites
./scripts/doctor.sh

# Pack context for long sessions
./scripts/context-pack.sh
```

## Anti-Patterns

❌ Making large changes without running tests
❌ Assuming code works without verification
❌ Modifying files outside the immediate task
❌ Leaving state files outdated
❌ Not reporting what commands were run
