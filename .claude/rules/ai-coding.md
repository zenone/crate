# AI Coding Rules (2026)

## Scope + chunking
- Prefer small, verifiable steps over big rewrites.
- If you need to touch many files, propose a plan first.

## Verification
- Always state how to verify changes (commands/tests).
- If you can’t run tests, say why and propose a fallback (unit tests, static checks).

## Context hygiene
- Keep `CLAUDE.md` short. Put long material in `.claude/`.
- Update `.claude/state/current-state.md` after meaningful progress.
- Add new gotchas to `.claude/knowledge-base/lessons-learned.md`.

## Safety
- Don’t introduce new dependencies or tooling without approval.
- Never add secrets to the repo.
