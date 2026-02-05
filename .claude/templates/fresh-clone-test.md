# Fresh Clone Test Template

**Purpose**: Verify your project works for new users/contributors.

## Before Any Release, Run:

```bash
# 1. Clone to temp directory (simulates new user)
git clone <your-repo> /tmp/fresh-clone-test
cd /tmp/fresh-clone-test

# 2. Check all essential files exist
ls -la *.sh *.py 2>/dev/null

# 3. Run doctor/setup
./scripts/doctor.sh || make doctor

# 4. Install dependencies
make install || pip install -e . || npm install

# 5. Run tests
make test || pytest || npm test

# 6. Start the app
make run || ./run.sh || npm start

# 7. Cleanup
rm -rf /tmp/fresh-clone-test
```

## Pre-Release Checklist

### Files & Git
- [ ] All essential scripts tracked: `git ls-files | grep -E '\.(sh|py)$'`
- [ ] No hardcoded paths: `grep -r '/Users/' . --include='*.sh' --include='*.py'`
- [ ] No hardcoded paths: `grep -r '/home/' . --include='*.sh' --include='*.py'`
- [ ] Check gitignore isn't hiding essentials: `git status --ignored`

### Script Portability
- [ ] All shell scripts use `SCRIPT_DIR` pattern:
  ```bash
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  ```
- [ ] Scripts work when run from different directory:
  ```bash
  cd /tmp && /path/to/repo/run.sh  # Should work!
  ```

### Documentation
- [ ] README has quick start instructions
- [ ] `.env.example` exists (if env vars needed)
- [ ] Dependencies documented (requirements.txt, package.json, pyproject.toml)
- [ ] Installation steps tested on fresh machine

### Verification Commands
```bash
# Check for hardcoded paths
grep -rn '/Users/\|/home/' --include='*.sh' --include='*.py' --include='*.ts' .

# Check SCRIPT_DIR pattern in shell scripts
for f in $(find . -name '*.sh' -type f); do
  if ! grep -q 'SCRIPT_DIR' "$f" 2>/dev/null; then
    echo "⚠️  Missing SCRIPT_DIR: $f"
  fi
done

# Verify tracked files
git ls-files | grep -E '\.(sh|py)$' | while read f; do
  echo "✓ Tracked: $f"
done
```

## Common Gotchas

1. **Gitignore patterns too broad**: `find_*.py` ignores `find_port.py` you need
   - Fix: Add `!find_port.py` to whitelist

2. **Script uses relative path**: `python3 find_port.py` fails from other dirs
   - Fix: `python3 "$SCRIPT_DIR/find_port.py"`

3. **Missing dependencies in package manifest**: Works locally (cached), fails on clone
   - Fix: Test in fresh venv/container

4. **Root daemon can't access user files**: macOS TCC blocks root from `~/.profile`
   - Fix: Check file accessibility before reading
