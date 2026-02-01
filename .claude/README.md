# Claude Code Template Project

## What Is This?

This is a **production-ready template** for starting any new software project with Claude Code CLI. It embeds best practices from 2025-2026, proven patterns from companies like Netflix, and official Anthropic guidance to ensure Claude consistently writes high-quality code.

## How It Works

Claude Code automatically reads files in specific locations:
- **Root `CLAUDE.md`**: Main instructions (this is your system prompt)
- **`.claude/rules/`**: Auto-loaded additional rules
- **`.claude/knowledge-base/`**: Persistent knowledge Claude references
- **`.claude/state/`**: Current project state (what's done, what's next)

When you start Claude Code in a project with this structure, it will:
1. Read all these files automatically
2. Follow the development workflows defined
3. Update knowledge base and state as work progresses
4. Never forget lessons learned across sessions

## Quick Start

### For a Brand New Project

```bash
# 1. Create new project directory
mkdir my-new-project && cd my-new-project

# 2. Copy this template
cp -r /path/to/template/CLAUDE.md ./
cp -r /path/to/template/.claude ./

# 3. Initialize git (FIRST THING!)
git init
git add .gitignore CLAUDE.md .claude/
git commit -m "Initial commit: Add Claude Code template"

# 4. Launch Claude Code
claude

# 5. First prompt: "Initialize this project following the template guidance"
```

Claude will then:
- Research best tech stack for your project type (2026 standards)
- Set up proper .gitignore
- Create project structure (API-first architecture)
- Set up TDD infrastructure
- Document decisions in `.claude/knowledge-base/`

### For Existing Projects

```bash
# 1. Copy template into existing project
cd existing-project
cp /path/to/template/CLAUDE.md ./
cp -r /path/to/template/.claude ./

# 2. Customize CLAUDE.md for your existing stack
# (edit CLAUDE.md to match your current tech choices)

# 3. Document current state
# (edit .claude/state/current-state.md with where project is now)

# 4. Launch Claude Code
claude

# 5. First prompt: "Review the existing codebase and update .claude/knowledge-base/ with findings"
```

## Directory Structure

```
project/
├── CLAUDE.md                          # Main instructions (auto-loaded)
├── .gitignore                         # Comprehensive ignore rules
│
├── .claude/                           # Persistent memory & configuration
│   ├── README.md                      # This file
│   │
│   ├── knowledge-base/                # Growing knowledge (never delete)
│   │   ├── lessons-learned.md         # Mistakes we've fixed (UPDATE OFTEN)
│   │   ├── tech-stack-decisions.md    # Technology choices & rationale
│   │   └── market-research.md         # User needs, competitor analysis
│   │
│   ├── state/                         # Current session state
│   │   └── current-state.md           # Where we are, what's next (UPDATE DAILY)
│   │
│   ├── workflows/                     # Reusable process templates
│   │   ├── feature-development.md     # How to build features
│   │   ├── quality-assurance.md       # QA checklist
│   │   └── github-preparation.md      # Prepare code for GitHub
│   │
│   ├── templates/                     # Prompt templates
│   │   ├── two-phase-prompt.md        # Planning + execution template
│   │   └── quality-checklist.md       # Pre-commit checklist
│   │
│   ├── skills/                        # Domain-specific knowledge (optional)
│   ├── commands/                      # Custom slash commands (optional)
│   ├── rules/                         # Additional rules (optional)
│   └── settings.json                  # Claude Code settings (optional)
│
├── core/                              # Business logic (API-first)
├── api/                               # API layer
├── cli/                               # CLI interface
├── ui/                                # GUI interface
└── tests/                             # Comprehensive test suite
```

## Key Files to Update Regularly

### Must Update After Every Session
- **`.claude/state/current-state.md`**: What you accomplished, what's next, any blockers

### Must Update When Learning
- **`.claude/knowledge-base/lessons-learned.md`**: Every bug, mistake, or "aha!" moment

### Must Update When Making Decisions
- **`.claude/knowledge-base/tech-stack-decisions.md`**: Why you chose X over Y
- **`.claude/knowledge-base/market-research.md`**: User needs you discovered

## Why This Structure?

### Persistence Across Sessions
When Claude's conversation compresses or you restart:
- No context lost (it's all in `.claude/`)
- No repeated mistakes (lessons-learned.md)
- Continuity (current-state.md tells Claude where you are)

### Team Collaboration
- Commit `CLAUDE.md` and `.claude/` to git
- Everyone gets same Claude behavior
- Institutional knowledge captured
- New team members onboard faster

### Quality Assurance
- TDD enforced by template
- Security gates built-in
- API-first architecture prevents tight coupling
- Quality checklists ensure nothing skipped

## Customization

### Project-Specific Rules
Add files to `.claude/rules/` for specific requirements:
```bash
# Example: Frontend-specific rules
echo "# Frontend Rules\n\n- Use TypeScript strict mode\n- All components must have tests\n" > .claude/rules/frontend.md
```

### Custom Commands
Add reusable prompts to `.claude/commands/`:
```bash
# Example: Debug command
cat > .claude/commands/debug.md << 'EOF'
# Debug Current Issue

1. Read error logs and stack traces
2. Identify root cause using TDD
3. Write failing test that reproduces bug
4. Fix bug while keeping all other tests passing
5. Add regression test
6. Update lessons-learned.md
EOF
```

Now you can run `/debug` in Claude Code.

### Team-Specific Skills
Add domain knowledge to `.claude/skills/`:
```bash
# Example: Deployment process
cat > .claude/skills/deploy.md << 'EOF'
# Deployment Process

Our deployment uses:
- CI/CD: GitHub Actions
- Staging: AWS ECS (us-west-2)
- Production: AWS ECS (us-east-1)
- Blue-green deployment strategy
- Rollback: Revert to previous task definition
EOF
```

## Workflow Examples

### Example 1: Adding a New Feature

```
You: "Add user authentication with JWT"

Claude:
1. Reads CLAUDE.md and .claude/knowledge-base/
2. Enters Phase 1 (planning):
   - Researches JWT best practices 2026
   - Proposes API-first architecture
   - Identifies edge cases and security risks
   - Shows you the plan
3. Gets your approval
4. Enters Phase 2 (implementation):
   - Writes tests first (TDD)
   - Implements core logic
   - Builds API endpoints
   - Adds CLI/UI that calls API
   - Runs all tests
   - Updates .claude/state/current-state.md
```

### Example 2: Resuming After a Break

```
You: (restart Claude after 2 weeks)

Claude:
1. Automatically reads .claude/state/current-state.md
2. "Last session you were implementing user auth. The API is done and tested.
   Next step is building the CLI interface. Ready to continue?"
```

### Example 3: Bug Fix

```
You: "There's a bug where users can't login on mobile"

Claude:
1. Reads .claude/knowledge-base/lessons-learned.md
2. "We had a similar mobile issue before (see lessons-learned.md #23).
   Let me check if it's the same root cause..."
3. Writes failing test that reproduces bug
4. Fixes bug
5. Adds regression test
6. Updates lessons-learned.md with new entry
```

## Best Practices

### ✅ Do This
- Update `.claude/state/current-state.md` after every session
- Add lessons learned immediately when you discover them
- Research tech stack choices before committing
- Keep CLAUDE.md concise (Claude has limited context)
- Commit `.claude/` directory to git (except settings.local.json)
- Use `/init` command when starting new projects

### ❌ Don't Do This
- Don't let lessons-learned.md get stale
- Don't skip updating current-state.md ("I'll remember")
- Don't put secrets in any files (especially .claude/)
- Don't make CLAUDE.md too verbose (wastes context window)
- Don't ignore the two-phase workflow (plan first!)
- Don't commit .claude/settings.local.json (personal settings)

## Troubleshooting

### Claude Isn't Following Template
**Problem**: Claude doesn't seem to read CLAUDE.md

**Solutions**:
1. Launch Claude from project root: `cd /path/to/project && claude`
2. Verify CLAUDE.md exists in current directory
3. Check for syntax errors in CLAUDE.md
4. Try: "Read CLAUDE.md and .claude/knowledge-base/ and summarize what you learned"

### Template Too Verbose
**Problem**: CLAUDE.md is consuming too much context

**Solutions**:
1. Move detailed workflows to `.claude/workflows/` (only load when needed)
2. Use `.claude/rules/` for optional rules (split by domain)
3. Keep CLAUDE.md high-level, reference other files for details

### Losing Context Between Sessions
**Problem**: Claude forgets what we were working on

**Solutions**:
1. Always update `.claude/state/current-state.md` before exiting
2. Include: what's done, what's next, current blockers, files changed
3. Reference specific file paths and line numbers
4. Use Task tool to write summary if conversation is long

## Advanced Usage

### Multi-Agent Workflows
Use Claude's built-in agents for complex tasks:
```
You: "Explore the codebase and identify all API endpoints"
Claude: (uses Explore agent to map out API surface)

You: "Plan the refactoring of auth system"
Claude: (uses Plan agent to create detailed implementation plan)
```

### Hooks & Automation
Add `.claude/settings.json` for automated workflows:
```json
{
  "hooks": {
    "pre-commit": "pytest tests/ && black . && flake8"
  }
}
```

### Memory Across All Projects
Put global rules in `~/.claude/CLAUDE.md`:
```bash
cat > ~/.claude/CLAUDE.md << 'EOF'
# Global Preferences

- I prefer descriptive variable names over short ones
- Always use type hints (Python) or TypeScript
- I like tests co-located with code (tests/ directory next to src/)
- Security > performance > developer experience (priority order)
EOF
```

## Support & Resources

### Official Documentation
- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)
- [CLAUDE.md Guide](https://claude.com/blog/using-claude-md-files)
- [Memory Management](https://code.claude.com/docs/en/memory)

### Community Resources
- [Complete CLAUDE.md Guide](https://www.builder.io/blog/claude-md-guide)
- [Dometrain: Perfect CLAUDE.md](https://dometrain.com/blog/creating-the-perfect-claudemd-for-claude-code/)
- [GitHub Showcase Example](https://github.com/ChrisWiles/claude-code-showcase)

---

**Remember**: This template is a living document. As you learn what works for your workflow, update it. The goal is to make Claude your perfect pair programmer, and that requires teaching it your preferences through these files.

**Start every project with this template, and you'll never start from zero again.**
