# Usage

## Create a new project

```bash
cd "~/Downloads/code/claude-code-template"
./scripts/new-project.sh ~/code/my-new-project "My New Project" [variant]

cd ~/code/my-new-project
git init
git add .
git commit -m "Initial commit from template"
```

## After creation
- `docs/STACK_DECISION.md` is created for you (timeboxed decision). Update it.
- `docs/LOCAL_DEV.md` is created for you. Update it.
- Wire `Makefile` targets to real commands.
- Optional: copy a variant CI scaffold (`variants/*/.github/workflows/ci.yml`).

## Helpful commands
Create a context bundle for dev sessions:
```bash
./scripts/context-pack.sh
```

Install opt-in git hooks (recommended):
```bash
./scripts/install-hooks.sh
```

Run the quality gate:
```bash
make verify
```

Sanity-check your machine:
```bash
./scripts/doctor.sh
```

## Updating the template
Keep the template itself clean:
- don’t commit `.claude/settings.local.json`
- keep `CLAUDE.md` short
- put long rules into `.claude/`
