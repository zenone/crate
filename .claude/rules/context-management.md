# Context Management Rules (2026)

## Critical Thresholds

Monitor token usage in the status bar (Claude Code) or model response quality.

| Zone | % | Action |
|------|---|--------|
| Green | 0-50% | Normal operation |
| Yellow | 50-75% | Plan exit point |
| Orange | 75-80% | Wrap up, update state, exit |
| Red | 80%+ | Quality degradation — exit immediately |

## Exit Protocol

When approaching 75-80%:
1. Update `.claude/state/current-state.md` with progress
2. Add any lessons to `knowledge-base/lessons-learned.md`
3. Exit cleanly

Next session will auto-load context from `.claude/` files.

## The /clear Command

Use `/clear` when switching between unrelated tasks to avoid context pollution.

**Use when:**
- Finished debugging → starting new feature
- Research complete → implementing
- One feature done → starting another

**Don't use:**
- Mid-task (you'll lose context)
- When tasks are related

## Subagent Delegation

For research-heavy tasks, delegate to subagents (Task tool) to preserve main session context.

**Delegate:**
- Tech stack research
- Best practices lookup
- Security audits
- Documentation review
- Library comparisons

**Keep in main session:**
- Implementation
- Testing
- Code review
- Bug fixes (unless investigation-heavy)

## Thinking Keywords

Trigger extended thinking for complex decisions:

| Keyword | Use When |
|---------|----------|
| `think` | Standard analysis |
| `think hard` | Architecture decisions |
| `think harder` | Security, performance |
| `ultrathink` | Critical system design |

Example: "Think hard about the best approach for distributed rate limiting."

## Anti-Patterns

❌ "Kitchen sink" sessions (mixing unrelated topics)
❌ Running to 90%+ context
❌ Asking for entire features in one prompt
❌ Not updating state before exit
