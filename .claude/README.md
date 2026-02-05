# .claude/

Persistent memory + workflows for AI-assisted coding.

Claude Code auto-loads:
- `CLAUDE.md` (repo root)
- `.claude/rules/*`
- `.claude/knowledge-base/*`
- `.claude/state/current-state.md`

## Directory Structure

```
.claude/
├── state/                    # Current project state
│   └── current-state.md      # What you're doing NOW (update frequently!)
│
├── knowledge-base/           # Persistent memory
│   ├── lessons-learned.md    # Mistakes and fixes
│   ├── tech-stack-decisions.md
│   ├── architecture-patterns.md
│   ├── debugging-patterns.md
│   ├── git-patterns.md
│   └── macos-patterns.md
│
├── rules/                    # Guardrails and guidelines
│   ├── ai-coding.md          # AI coding best practices
│   ├── self-review.md        # Review→fix loop before presenting
│   ├── systematic-reasoning.md
│   ├── safety-snapshots.md   # Create backups before risky changes
│   ├── human-checkpoints.md  # When to pause for human verification
│   ├── dead-code.md          # Finding and removing unused code
│   ├── code-quality-tools.md # Quick reference for linting/formatting
│   ├── security.md
│   ├── testing.md
│   ├── error-handling.md
│   └── git.md
│
├── workflows/                # Step-by-step processes
│   ├── feature-development.md
│   ├── quality-assurance.md
│   ├── github-preparation.md
│   ├── quick-reference.md
│   └── versioning.md
│
├── templates/                # Reusable prompts and checklists
│   ├── two-phase-prompt.md   # Prompt compiler workflow
│   ├── quality-checklist.md
│   ├── pre-publish-checklist.md
│   ├── readme-guide.md       # How to write great READMEs
│   └── fresh-clone-test.md
│
└── commands/                 # Claude Code slash commands
    ├── init.md
    ├── ship.md
    └── stack.md
```

## What to Keep Updated

**Every session**:
- `state/current-state.md` — What are you working on? What's next?

**When you learn something**:
- `knowledge-base/lessons-learned.md` — Mistakes, gotchas, solutions

**When you make tech decisions**:
- `knowledge-base/tech-stack-decisions.md` — Why you chose X over Y

## Local-only Config

Copy and customize:
```bash
cp .claude/settings.example.json .claude/settings.local.json
```

`settings.local.json` is gitignored.

## Key Workflows

| Task | Workflow |
|------|----------|
| Build a feature | `workflows/feature-development.md` |
| QA before commit | `workflows/quality-assurance.md` |
| Push to GitHub | `workflows/github-preparation.md` |
| Complex task | `templates/two-phase-prompt.md` |
| Release version | `templates/pre-publish-checklist.md` |
