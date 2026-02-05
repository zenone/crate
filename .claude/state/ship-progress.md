# Ship Progress (GitHub)

Tracks execution of `./.claude/GITHUB_SHIP_TASKS.md`.

## Snapshot / rollback
- [x] Confirm clean working tree
- [x] Create snapshot tag/branch (`ship-snapshot-2026-02-04` @ c10140c6)
- [x] Record snapshot in `.claude/state/current-state.md`

## A — Repo hygiene
- [x] A1 runtime artifacts / .gitignore (verified; removed local stray pid/coverage files; expanded ignore patterns)
- [x] A2 secrets scan (no keys/tokens found)
- [x] A3 remove AI-authorship comments (none found in shipped docs/code)

## B — Code review
- [x] B1 business logic audit (rename stays in same directory; collision handling; atomic os.replace)
- [ ] B2 safe dead-code removal (only if provably unused; keep diffs minimal)

## C — Security review
- [x] C1 web attack surface pass (CORS default-off; Origin guard on execute/stream/undo)
- [ ] C2 threat model write-up + final high/critical issue scan

## C — Security review
- [ ] C1 threat model
- [ ] C2 fix critical/high issues + tests

## D — Testing & verification
- [ ] D1 pytest
- [ ] D2 mypy + ruff
- [ ] D3 Manual smoke test breakpoint (user)

## E — Branding / docs
- [ ] E1 naming consistency
- [ ] E2 no legacy names
- [ ] E3 README refresh

## F — GitHub publishing
- [ ] F1 decide push strategy
- [ ] F2 push
- [ ] F3 post-push verification
