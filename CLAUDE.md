# Project Template - AI Coding Guidance (Claude/Cursor)

This file is intentionally **short**. It sets the working contract and points you to the repo's persistent memory.

## Prime directive
Ship correct, minimal changes with high confidence.

## Always start by reading
1) `.claude/state/current-state.md`
2) `.claude/knowledge-base/tech-stack-decisions.md`
3) `.claude/knowledge-base/lessons-learned.md`
4) If relevant, a workflow:
   - `.claude/workflows/feature-development.md`
   - `.claude/workflows/quality-assurance.md`
   - `.claude/workflows/github-preparation.md`

## Default workflow (2026 AI-assisted)
- **Spec before code**: if requirements aren't crisp, ask a few targeted questions then propose a short plan + acceptance criteria.
- **Stack selection (when unknown)**: propose 1-3 viable stacks and recommend one, with brief rationale + tradeoffs. Timebox research; don't bikeshed.
- **Small chunks**: implement one step at a time; run tests between steps.
- **TDD where it pays**: new logic gets tests; small glue code can be pragmatic.
- **Verification is part of the task**: always include exact commands you ran.

## Rules of engagement
- Prefer the smallest viable diff. No unrelated refactors.
- When changing behavior, add/adjust tests.
- Never commit secrets. Use `.env.example` + runtime env vars.
- If you are unsure, say what you're assuming and how you'll validate.
- **Self-review code before presenting**: fix issues you can catch (see `.claude/rules/self-review.md`).
- **Use structured reasoning** for complex decisions (see `.claude/rules/systematic-reasoning.md`).
- **Update `.claude/state/current-state.md` after every meaningful change or at session end.**

## Deliverable format (every response)
- **Summary** (1-3 bullets)
- **Files changed** (paths)
- **How to test** (commands)
- **Risks / edge cases** (if any)

## Where the "real" guidance lives
- Deep best practices: `.claude/BEST_PRACTICES_2026.md`
- Checklists/templates: `.claude/templates/`
- Persistent memory: `.claude/knowledge-base/`
- Current focus: `.claude/state/current-state.md`

(Older verbose version saved at `docs/legacy/CLAUDE.full.md`.)
