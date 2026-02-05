# Git Workflow Patterns

Patterns for effective version control in AI-assisted development.

---

## Commit Hygiene

### Atomic Commits

**Pattern**: One logical change per commit.

**Good**:
```bash
git commit -m "feat: Add user authentication endpoint"
git commit -m "test: Add tests for authentication"
git commit -m "docs: Document authentication API"
```

**Bad**:
```bash
git commit -m "Add auth, fix bug, update docs, refactor utils"
```

**Why**: Atomic commits enable:
- Easy reverts (`git revert` one feature, not five)
- Meaningful `git bisect`
- Clean PR reviews
- Clear changelog generation

---

### Conventional Commits

**Format**: `type(scope): description`

**Types**:
| Type | When |
|------|------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting (no code change) |
| `refactor` | Code change that neither fixes nor adds |
| `perf` | Performance improvement |
| `test` | Adding/updating tests |
| `chore` | Maintenance (deps, config) |

**Examples**:
```bash
feat(auth): Add JWT token refresh endpoint
fix(api): Handle null user in profile endpoint
docs(readme): Add installation instructions
refactor(core): Extract validation to separate module
test(auth): Add tests for token expiration
chore(deps): Upgrade fastapi to 0.110.0
```

---

## Branch Strategies

### Feature Branches

**Pattern**: One branch per feature/fix.

```bash
# Create feature branch
git checkout -b feat/user-authentication

# Work on feature...
git commit -m "feat(auth): Add login endpoint"
git commit -m "test(auth): Add login tests"

# Merge back
git checkout main
git merge feat/user-authentication
git branch -d feat/user-authentication
```

### Branch Naming

```
feat/short-description    # New feature
fix/issue-123            # Bug fix (with issue number)
refactor/module-name     # Refactoring
docs/topic               # Documentation
test/component           # Test additions
```

---

## History Rewriting (Safely)

### Interactive Rebase

**When**: Clean up commits before pushing/merging.

```bash
# Rebase last 3 commits
git rebase -i HEAD~3

# In editor:
pick abc123 First commit
squash def456 WIP: more work        # Combine with previous
reword ghi789 Fix typo in message   # Edit message
```

**Commands**:
- `pick` - Keep commit as-is
- `reword` - Keep commit, edit message
- `squash` - Combine with previous commit
- `fixup` - Combine, discard message
- `drop` - Delete commit

### Amend Last Commit

```bash
# Forgot a file
git add forgotten-file.py
git commit --amend --no-edit

# Fix commit message
git commit --amend -m "Better message"
```

**Warning**: Never rewrite history that's been pushed to shared branches.

---

## Dealing with Mistakes

### Undo Last Commit (Keep Changes)

```bash
git reset --soft HEAD~1
# Changes are now staged
```

### Undo Last Commit (Discard Changes)

```bash
git reset --hard HEAD~1
# Changes are gone (recoverable via reflog for 30 days)
```

### Recover Deleted Commit

```bash
git reflog                    # Find commit hash
git checkout <hash>           # Detached HEAD at that commit
git checkout -b recovery      # Create branch to save it
```

### Undo a Push (Force Push)

```bash
git reset --hard HEAD~1
git push --force-with-lease   # Safer than --force
```

**Warning**: Only do this on your own branches, never on `main`.

---

## Stashing

### Save Work in Progress

```bash
git stash                     # Stash tracked changes
git stash -u                  # Include untracked files
git stash save "WIP: auth"    # With message

# Later...
git stash list                # See stashes
git stash pop                 # Apply and remove
git stash apply               # Apply but keep stash
git stash drop stash@{0}      # Delete specific stash
```

### Partial Stash

```bash
git stash -p                  # Interactive: choose hunks to stash
```

---

## Handling Merge Conflicts

### Resolution Pattern

```bash
# During merge conflict
git status                    # See conflicted files

# Edit files, look for conflict markers:
<<<<<<< HEAD
your changes
=======
their changes
>>>>>>> branch-name

# After resolving:
git add resolved-file.py
git merge --continue          # Or git rebase --continue
```

### Conflict Prevention

```bash
# Before starting work, sync with main
git checkout main
git pull
git checkout -b feat/new-feature

# Periodically sync during long-running branches
git fetch origin
git rebase origin/main        # Or merge, based on team convention
```

---

## git-filter-repo Over filter-branch

**Pattern**: Use `git-filter-repo` for history rewriting tasks.

**Why**:
- `git filter-branch` is deprecated
- `git-filter-repo` is faster and safer
- Better handling of edge cases

**Installation**:
```bash
pip install git-filter-repo
```

**Common Uses**:

Remove file from entire history:
```bash
git filter-repo --path secrets.env --invert-paths
```

Remove author from history:
```bash
git filter-repo --commit-callback '
    if commit.author_name == b"Bot Name":
        commit.author_name = b"Real Author"
        commit.author_email = b"real@example.com"
'
```

Change commit messages:
```bash
git filter-repo --message-callback '
    return message.replace(b"old text", b"new text")
'
```

---

## Signed Commits

### SSH Signing (Modern, Recommended)

```bash
# Configure
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
git config --global commit.gpgsign true

# Sign commit
git commit -S -m "Signed commit"

# Verify
git log --show-signature
```

### GPG Signing (Traditional)

```bash
git config --global user.signingkey YOUR_GPG_KEY_ID
git config --global commit.gpgsign true
```

---

## Worktrees (Multiple Branches Simultaneously)

**When**: Need to work on multiple branches without stashing.

```bash
# Create worktree for hotfix while staying on feature
git worktree add ../project-hotfix hotfix/urgent-bug

# Work in ../project-hotfix (separate directory, same repo)
cd ../project-hotfix
# ... make fixes ...
git commit -m "fix: Urgent bug"

# Clean up
git worktree remove ../project-hotfix
```

**Benefits**:
- No stashing/switching
- Run tests on one branch while coding on another
- Separate IDE windows per branch

---

## Hooks for Quality Gates

### Pre-commit Hook

`.git/hooks/pre-commit`:
```bash
#!/bin/bash
set -e

echo "Running pre-commit checks..."

# Format check
black --check . || (echo "❌ Run: black ." && exit 1)

# Lint
flake8 src/ || (echo "❌ Linting failed" && exit 1)

# Tests
pytest tests/ -q || (echo "❌ Tests failed" && exit 1)

echo "✅ All checks passed"
```

```bash
chmod +x .git/hooks/pre-commit
```

### Shared Hooks (via .githooks/)

```bash
# In repo
mkdir .githooks
# Add hook scripts to .githooks/

# Configure git to use them
git config core.hooksPath .githooks
```

---

## Quick Reference

```bash
# Status
git status -s                 # Short status
git log --oneline -10         # Recent commits
git diff --stat               # Summary of changes

# Branches
git branch -a                 # All branches (local + remote)
git branch -d branch          # Delete merged branch
git branch -D branch          # Force delete branch

# Remote
git remote -v                 # Show remotes
git fetch --all --prune       # Sync all remotes, remove stale

# Clean
git clean -fd                 # Remove untracked files/dirs
git clean -fXd                # Remove ignored files too

# Blame
git blame file.py             # Who wrote each line
git blame -L 10,20 file.py    # Lines 10-20 only
```
