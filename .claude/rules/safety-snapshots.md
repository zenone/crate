# Safety Snapshots

## When to Snapshot

**Before any risky operation**, create a recovery point:
- Large refactoring (>10 files)
- Dependency upgrades
- Database migrations
- Rebranding / renaming
- "Cleanup" operations
- Anything described as "delete", "remove", "clean"

## How to Snapshot

### Option 1: Git Tag (Preferred)
```bash
# Create snapshot tag with timestamp
git add -A
git commit -m "snapshot: pre-refactoring state"
git tag snapshot-$(date +%Y%m%d-%H%M%S)

# List snapshots
git tag | grep snapshot

# Restore if needed
git checkout snapshot-20260205-133000
```

### Option 2: Git Stash (Quick)
```bash
git stash push -m "pre-refactoring snapshot"

# Restore if needed
git stash list
git stash pop
```

### Option 3: Directory Copy (Last Resort)
```bash
# Only when git isn't available or trusted
cp -r project project-snapshot-$(date +%Y%m%d-%H%M%S)
```

## Snapshot Naming Convention

```
snapshot-YYYYMMDD-HHMMSS-description
```

Examples:
- `snapshot-20260205-133000-pre-rebrand`
- `snapshot-20260205-140000-before-dep-upgrade`
- `snapshot-20260205-150000-working-state`

## Golden Rule

**If the code is working now**, snapshot it before touching anything risky.

"I'll just make a quick change" is how working code becomes broken code with no recovery path.

## Recovery Workflow

```bash
# Something broke? Check your snapshots
git tag | grep snapshot

# View what changed since snapshot
git diff snapshot-20260205-133000

# Full restore (nuclear option)
git checkout snapshot-20260205-133000
git checkout -b recovery-branch

# Selective restore (one file)
git checkout snapshot-20260205-133000 -- path/to/file.py
```

## Integration with Workflow

Add to your pre-work checklist:
1. ✅ Run tests (confirm working state)
2. ✅ Create snapshot
3. ✅ Document what you're about to do
4. 🔄 Make changes
5. ✅ Test after each change
6. ❌ If broken → restore from snapshot
