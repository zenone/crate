# AUDIT-GATES.md — Crate Project
# Living register of design invariants. One gate per committed decision.
#
# Runner: bash ~/Dropbox/.nimbus-shared/scripts/audit-gates-check.sh /path/to/crate
# Or:     make audit-gates  (from project root)
#
# Rule: Gate PASSES if command produces zero output.
#       Gate FAILS  if command produces any output (describes what's broken).
#
# Adding a gate: when you commit a design decision, architectural constraint,
# or "this must never happen" rule — add a gate HERE in the same commit.
# Run `make audit-gates` to verify the gate works on a correct system.
# If it produces output on a correct system, fix the command, not the code.

---

## D-001 — No standalone "AI" word in public-facing text
**Invariant:** README, docs text files, and web templates must not use the bare word "AI" (use "audio analysis", "audio features", etc. instead). Lesson from 2026-02-07.
**Command (gate fails if output non-empty):**
```bash
grep -rn '\bAI\b' \
  /Users/szenone/Code/labs/python/DJ/crate/README.md \
  /Users/szenone/Code/labs/python/DJ/crate/docs \
  2>/dev/null \
  | grep -v "^Binary" \
  | grep -v "^$"
```
**Pass:** zero output

---

## D-002 — RenameRequest model must define dry_run field
**Invariant:** The `dry_run` field in `RenameRequest` is a critical safety contract — it must never be removed or renamed.
**Command (gate fails if output non-empty):**
```bash
python3 -c "
import ast, sys
src = open('/Users/szenone/Code/labs/python/DJ/crate/crate/api/models.py').read()
tree = ast.parse(src)
found = False
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef) and node.name == 'RenameRequest':
        for item in ast.walk(node):
            if isinstance(item, ast.AnnAssign):
                if hasattr(item.target, 'id') and item.target.id == 'dry_run':
                    found = True
if not found:
    print('VIOLATION: RenameRequest.dry_run field missing from crate/api/models.py')
"
```
**Pass:** zero output

---

## D-003 — File rename/move must not bypass API layer (CLI + TUI stay clean)
**Invariant:** CLI and TUI modules must never call `os.replace`, `os.rename`, or `shutil.move` directly — all rename operations must go through the API layer which enforces dry_run.
**Command (gate fails if output non-empty):**
```bash
grep -rn "os\.replace\|os\.rename\|shutil\.move" \
  /Users/szenone/Code/labs/python/DJ/crate/crate/cli \
  /Users/szenone/Code/labs/python/DJ/crate/crate/tui \
  2>/dev/null \
  | grep -v "__pycache__" \
  | grep -v "^$"
```
**Pass:** zero output

---

## D-004 — No hardcoded API keys or tokens in source
**Invariant:** No literal API key, token, or password strings hardcoded in tracked source files. Use environment variables instead.
**Command (gate fails if output non-empty):**
```bash
grep -rEn \
  '(api_key|api_token|secret_key|password)\s*=\s*"[A-Za-z0-9_\-]{12,}"' \
  /Users/szenone/Code/labs/python/DJ/crate/crate \
  /Users/szenone/Code/labs/python/DJ/crate/web \
  2>/dev/null \
  | grep -v "\.pyc" \
  | grep -v "__pycache__" \
  | grep -v "example\|placeholder\|YOUR_"
```
**Pass:** zero output

---

## D-005 — Python version constraint must exclude 3.14+ (Essentia wheel gap)
**Invariant:** `pyproject.toml` must specify `python_requires` that excludes Python 3.14+ until Essentia wheels are available. Lesson from 2026-02-07: Essentia has no 3.14 wheels.
**Command (gate fails if output non-empty):**
```bash
python3 -c "
import re, sys
content = open('/Users/szenone/Code/labs/python/DJ/crate/pyproject.toml').read()
# Check requires-python is set and constrains the upper bound
match = re.search(r'requires-python\s*=\s*[\"\'](.*?)[\"\']', content)
if not match:
    print('VIOLATION: requires-python not set in pyproject.toml')
    sys.exit()
spec = match.group(1)
# Must have an upper bound (<3.14 or <=3.13 or similar)
if not re.search(r'<\s*3\.1[4-9]|<\s*4|<=\s*3\.1[0-3]', spec):
    print(f'VIOLATION: requires-python=\"{spec}\" has no upper bound blocking Python 3.14+ (Essentia wheel gap)')
"
```
**Pass:** zero output

---

## Adding New Gates

Every time you commit a design decision, add an entry here **in the same commit**.

```markdown
## D-NNN — Short description of what this gate guards
**Invariant:** What must always be true.
**Command (gate fails if output non-empty):**
\`\`\`bash
<bash command that produces output ONLY when the invariant is violated>
\`\`\`
**Pass:** zero output
```

Rules:
1. Zero output = pass. Any output = fail.
2. Run `make audit-gates` before committing — the gate must pass on a correct system.
3. Use absolute paths (gates run from audit context, not project root).
4. Keep each gate under 5 seconds.
5. D-NNN numbers are sequential and never reused.
