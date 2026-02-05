# AI workflow (2026)

## The loop
1) Clarify goal + constraints (or write a short spec in `PROJECT.md`)
2) Make a plan (small steps)
3) Implement one step
4) Run tests / checks
5) Commit / document lessons

## Prompt patterns
- “Ask 3–5 questions before coding, then propose a plan + acceptance criteria.”
- “Make the smallest viable diff. No refactors unless requested.”
- “Show exact commands to verify.”

## Context management
- Keep `CLAUDE.md` short; long docs live in `.claude/`.
- Update `.claude/state/current-state.md` before you stop.
- Put recurring gotchas into `.claude/knowledge-base/lessons-learned.md`.
