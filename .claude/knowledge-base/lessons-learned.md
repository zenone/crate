# Lessons Learned

**Purpose**: Document every mistake, bug, or "aha!" moment so we never repeat them. This file grows over time and becomes institutional knowledge.

**Format**: Each entry should include date, problem, root cause, solution, and prevention strategy.

---

## How to Use This File

### When to Add an Entry
- Fixed a bug → Document what caused it and how to prevent it
- Made a wrong technology choice → Document why and what to choose instead
- Discovered a gotcha or edge case → Document it
- Learned a best practice → Document it
- Spent > 30 minutes on something that should have been simple → Document why

### Entry Template
```markdown
## [YYYY-MM-DD] Brief Title

**Context**: What were we trying to do?

**Problem**: What went wrong?

**Root Cause**: Why did it happen?

**Solution**: How did we fix it?

**Prevention**: How do we avoid this in the future?

**Related Files**: `path/to/file.py:123`

**Tags**: #security #api #testing #architecture
```

---

## Lessons

### [2026-02-01] Template Initialization

**Context**: Creating reusable Claude Code project template

**Problem**: Needed to consolidate multiple prompt systems and best practices into single coherent framework

**Solution**:
- Research official Claude Code documentation
- Created `.claude/` structure with knowledge-base, state, workflows, templates
- Wrote comprehensive CLAUDE.md as main system prompt
- Separated concerns: workflows vs knowledge vs state

**Prevention**: Always start new projects by copying this template structure

**Tags**: #meta #template #initialization

---

### Common Anti-Patterns to Avoid

#### 1. Repository Cleanup Gone Wrong
**Problem**: Running "cleanup" that deletes working development tools (like .venv)

**Prevention**:
- "Repository cleanup for GitHub" means preventing unwanted files from being pushed, not deleting local files
- Use .gitignore for exclusion, not deletion
- Never delete: .venv, node_modules, .env (add to .gitignore instead)

**Tags**: #git #cleanup

---

#### 2. Editing Before Reading
**Problem**: Making changes to files without reading them first

**Prevention**:
- ALWAYS read affected files before editing
- Understand existing patterns before adding new code
- Check for edge cases and existing error handling

**Tags**: #workflow #code-quality

---

#### 3. Testing at the End
**Problem**: Writing all implementation code first, then trying to test it

**Prevention**:
- Follow TDD strictly: test first, then implement
- Test after every change, not just at the end
- Catch regressions early when they're cheap to fix

**Tags**: #testing #tdd

---

#### 4. Stale Documentation
**Problem**: Not updating .claude/ files immediately, leading to lost context later

**Prevention**:
- Update `.claude/state/current-state.md` after EVERY session
- Add to lessons-learned.md as soon as you learn something
- "I'll remember" is a lie - write it down now

**Tags**: #documentation #memory

---

#### 5. Unmaintained Dependencies
**Problem**: Choosing libraries without checking maintenance status, causing issues later

**Prevention**:
- Before adding dependency, check: last commit date, issue response time, GitHub stars/forks
- Research "best [library] 2026" to find current recommendations
- Prefer actively maintained projects
- Check Stack Overflow for common issues

**Tags**: #dependencies #research

---

## Category Index

### Security
- [Link to security-related lessons as they're added]

### API Design
- [Link to API-related lessons as they're added]

### Testing
- [2026-02-01] Testing at the End (see above)

### Architecture
- [2026-02-01] Template Initialization (see above)

### Git/Version Control
- [2026-02-01] Repository Cleanup Gone Wrong (see above)

### Performance
- [Link to performance-related lessons as they're added]

### UI/UX
- [Link to UI/UX-related lessons as they're added]

---

## Statistics

- **Total Lessons**: 5
- **Last Updated**: 2026-02-01
- **Most Common Tags**: #testing, #git, #documentation

---

*This file should grow continuously. A healthy project will have dozens to hundreds of entries over time. If this file isn't growing, we're not learning.*
