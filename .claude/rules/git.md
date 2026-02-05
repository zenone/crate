# Git Rules

## Commit Hygiene
- Keep commits small and descriptive (why > what).
- Avoid formatting-only commits unless explicitly requested.
- Prefer one logical change per commit.
- Don't commit secrets or local config.

## Gitignore Best Practices
- **Whitelist essential files**: If `.gitignore` has patterns like `find_*.py` or `install-*.sh`, use negation (`!essential-file.sh`) to keep critical scripts tracked.
- **Verify tracking after adding scripts**: `git ls-files | grep scriptname`
- **Test fresh clones**: After any gitignore change, verify: `git clone <repo> /tmp/test && ls /tmp/test/`

## Script Portability (Critical!)
All shell scripts MUST work from any directory:

```bash
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
# Now use relative paths safely
```

**Why**: Scripts invoked via cron, systemd, or other directories break if they use bare relative paths.

## Naming & Rebranding
- **Name it right on day 1**: Renaming later is expensive (imports, paths, configs, system directories).
- **If you must rename**: Do it atomically in one session, test everything, update all references.

## Pre-Release Audit
Before any release:
- [ ] All essential scripts tracked (`git ls-files`)
- [ ] No hardcoded user paths (grep for `/Users/` or `/home/`)
- [ ] Scripts work from any directory
- [ ] Fresh clone works: `git clone <repo> /tmp/test && cd /tmp/test && ./run.sh`
