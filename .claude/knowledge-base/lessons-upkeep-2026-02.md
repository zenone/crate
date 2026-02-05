# Lessons Learned: Upkeep Project (2026-02)

## 1. Never Gitignore Essential Scripts
- **Context**: `find_port.py`, `install-daemon.sh` were gitignored, breaking fresh clones
- **Pattern**: `.gitignore` had `find_*.py` and `install-*.sh` patterns
- **Fix**: Whitelist essential files with `!filename` in .gitignore
- **Rule**: After adding any script, verify with `git ls-files | grep scriptname`

## 2. Scripts Must Work From Any Directory
- **Context**: `run-web.sh` failed when run from different directory
- **Pattern**: Used relative paths like `python3 find_port.py`
- **Fix**: Add `SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"` and use `$SCRIPT_DIR/`
- **Rule**: All shell scripts should `cd` to their own directory first

## 3. Kill Features That Don't Work
- **Context**: TUI had persistent layout/async bugs across multiple sessions
- **Decision**: Removed 2,054 lines of TUI code, shipped web-only
- **Lesson**: A polished single interface > buggy multiple interfaces
- **Rule**: If a feature has 3+ sessions of debugging without resolution, cut it

## 4. API-First Architecture
- **Pattern**: `api/` layer consumed by both `web/` and `cli/`
- **Benefit**: Same logic, tested once, consistent behavior
- **Implementation**: Never import from `core/` in UI layers
- **Structure**:
  ```
  api/          → Business logic (tested)
  web/          → Consumes API
  cli/          → Consumes API
  core/         → Low-level utilities (API only)
  ```

## 5. Daemon + Job Queue for Privileged Operations
- **Problem**: Web server can't run sudo commands safely
- **Solution**: Root daemon watches job queue, web server writes jobs
- **Files**:
  - `/var/local/appname-jobs/` - Job queue directory
  - `/Library/LaunchDaemons/com.appname.daemon.plist` - Daemon config
- **Lesson**: Clean privilege separation = no password prompts in UI

## 6. State Files Over Agent Memory
- **What persists**: `~/.appname/config.json`, operation history
- **What doesn't**: Agent context between sessions
- **Rule**: If it matters tomorrow, write it to disk today
- **Pattern**: JSON files in `~/.appname/` for user config

## 7. Preview Mode for Destructive Operations
- **Pattern**: `--preview` shows what would happen without doing it
- **UX Win**: Users trust tools that let them look before leaping
- **Implementation**: Same code path, just skip the `execute()` call
- **Rule**: Any delete/modify operation should have preview mode

## 8. TypeScript for Web Frontends
- **Initial thought**: "It's just a dashboard, vanilla JS is fine"
- **Reality**: Types caught 10+ bugs during refactoring
- **Setup cost**: 5 minutes (ESBuild + tsconfig.json)
- **Rule**: Always use TypeScript for any JS > 200 lines

## 9. Two-Phase Development Workflow
- **Phase 1 (Plan)**: Requirements, approach, edge cases, get approval
- **Phase 2 (Execute)**: Implement, test, ship
- **Benefit**: Prevents scope creep and "just one more thing"
- **Rule**: Never start coding without a written plan

## 10. Audit Scripts in Git Before Release
- **Checklist**:
  - [ ] All essential scripts tracked (`git ls-files`)
  - [ ] No hardcoded paths (use `$SCRIPT_DIR` or `$HOME`)
  - [ ] Scripts work from any directory
  - [ ] Fresh clone works without manual steps
- **Command**: `git clone <repo> /tmp/test && cd /tmp/test && ./run.sh`

## 11. Rebrand Early or Never
- **Context**: mac-maintenance → Upkeep rename
- **Pain**: 50+ files, paths, imports, system directories
- **Lesson**: Name it right on day 1, or accept the name forever
- **If renaming**: Do it in one atomic session, test everything

## 12. Root Daemon Can't Access User Files (macOS TCC)
- **Context**: macOS Transparency, Consent, and Control blocks root from user directories
- **Symptom**: `Operation not permitted` on ~/.profile, ~/.gitconfig
- **Fix**: Check file accessibility before reading/writing, provide helpful fallback
- **Rule**: Never assume root can access user files on modern macOS
