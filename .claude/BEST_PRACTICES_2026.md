# Claude Code Best Practices (2026)

**Last Updated**: 2026-02-01
**Sources**: Official Anthropic documentation + community research

This document captures current (2026) best practices for working with Claude Code CLI, based on official guidance and community research.

---

## 📊 Research Summary

### Sources Consulted

1. [Claude Code: Best Practices for Agentic Coding](https://www.anthropic.com/engineering/claude-code-best-practices) - Official Anthropic
2. [Best Practices for Claude Code (Official Docs)](https://code.claude.com/docs/en/best-practices)
3. [Claude Code Context Optimization (54% Reduction)](https://gist.github.com/johnlindquist/849b813e76039a908d962b2f0923dc9a)
4. [How Claude Code Got Better by Protecting More Context](https://hyperdev.matsuoka.com/p/how-claude-code-got-better-by-protecting)
5. [CLAUDE.md Best Practices (Arize)](https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/)
6. [Optimizing Agentic Coding 2026](https://research.aimultiple.com/agentic-coding/)
7. [Claude Prompt Engineering Best Practices 2026](https://promptbuilder.cc/blog/claude-prompt-engineering-best-practices-2026)
8. [Claude Code in 2026: End-to-End SDLC Workflow](https://developersvoice.com/blog/ai/claude_code_2026_end_to_end_sdlc/)

---

## 🎯 Critical Best Practices

### 1. Context Window Management

#### Exit at 75-80% Utilization ⭐ CRITICAL
**What**: Monitor token percentage in status bar. Exit and restart when reaching 75-80%.

**Why**: Performance degrades near limits:
- More bugs slip through
- Architectural decisions become inconsistent
- Earlier project-specific patterns get forgotten
- Quality deteriorates despite more raw output

**How**:
```bash
# When status bar shows 75-80%, exit:
exit

# Start fresh session:
claude

# Claude will auto-load CLAUDE.md and .claude/ files
```

**Research**: "Sessions that stop at 75% utilization produce less total output but higher-quality, more maintainable code that actually ships." ([Source](https://hyperdev.matsuoka.com/p/how-claude-code-got-better-by-protecting))

---

#### Use /clear Between Unrelated Tasks ⭐ CRITICAL
**What**: Run `/clear` command when switching topics.

**Why**: "Kitchen sink sessions" fill context with irrelevant information:
- You start with task A
- Ask about unrelated topic B
- Return to task A
- Context is now polluted with B's information

**How**:
```bash
# After completing debugging:
/clear

# Before starting new feature:
# (context is now clean)
```

**When to use**:
- After finishing a feature
- Before investigating a bug
- When switching from research to implementation
- After long research sessions

---

### 2. CLAUDE.md Optimization

#### Keep It Concise: Quality Over Quantity ⭐ CRITICAL
**What**: Optimize CLAUDE.md for minimal context usage while preserving capability.

**Target**: Keep CLAUDE.md under 400 lines. Move detailed protocols to `.claude/` subdirectories.

**What to Keep**:
- Core principles (API-first, TDD, security-first)
- Non-obvious project-specific rules
- Critical workflows (two-phase, quality gates)
- Persistent state management instructions

**What to Remove** (discoverable from code/README):
- Detailed step-by-step guides → Move to `.claude/workflows/`
- Long checklists → Move to `.claude/templates/`
- Architecture diagrams → In README.md or docs/
- Command lists → Claude can discover via `ls`, `make help`, etc.
- Package structure details → Claude can read code structure
- Build commands → In Makefile or package.json
- Testing commands → In package.json scripts or Makefile
- Environment variables list → In .env.example

**Research**: "A 54% reduction in initial context means more room for actual work, faster responses, and lower costs—without sacrificing capability." ([Source](https://gist.github.com/johnlindquist/849b813e76039a908d962b2f0923dc9a))

**Lazy Loading Principle**: "Claude only needs to know when to invoke a skill. The skill's SKILL.md file contains the detailed protocol, loaded on-demand."

---

### 3. Subagent Usage for Context Preservation

#### Delegate Research & Investigation ⭐ IMPORTANT
**What**: Use Task tool with subagents for research, not main session.

**Why**: Each subagent gets its own context window, preventing main session bloat.

**When to use subagents**:
- Tech stack research
- Best practices lookup
- Bug investigation
- Security audits
- Performance profiling
- API documentation review
- Library comparison

**How**:
```
You: "We need to add authentication. Research JWT best practices for 2026 and propose implementation."

Claude: (uses Task tool with general-purpose agent for research)
Agent: (researches in its own context window)
Agent: (returns findings)

Claude: (receives summary without context pollution)
Claude: Now implements based on research
```

**Research**: "The best practice is to 'divide and conquer with sub-agents: modularize large objectives. Delegate API research, security review, or feature planning to specialized sub-agents'. Each subagent gets its own context window, preventing any single session from approaching limits." ([Source](https://hyperdev.matsuoka.com/p/how-claude-code-got-better-by-protecting))

---

### 4. Extended Thinking Mode

#### Use Thinking Keywords for Complex Problems ⭐ IMPORTANT
**What**: Trigger extended thinking with specific keywords.

**Keywords** (increasing thinking budget):
- `think` - Standard thinking budget
- `think hard` - Increased thinking budget
- `think harder` - More thorough analysis
- `ultrathink` - Maximum thinking budget

**When to use**:
- Architecture decisions
- Security reviews
- Complex algorithms
- Performance optimization
- Design pattern selection
- Error handling strategy

**Example**:
```
You: "Think hard about the best way to implement rate limiting for our API.
     Consider distributed systems, Redis vs in-memory, and failure modes."

Claude: (allocates more computation time)
Claude: (evaluates alternatives more thoroughly)
Claude: (provides well-reasoned recommendation)
```

**Research**: "We recommend using the word 'think' to trigger extended thinking mode, which gives Claude additional computation time to evaluate alternatives more thoroughly." ([Source](https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/))

---

## 🚀 Important Best Practices

### 5. Planning Before Coding

#### Research and Plan First
**What**: Don't jump straight to implementation.

**Why**: "Without research and planning steps, Claude tends to jump straight to coding a solution. Asking Claude to research and plan first significantly improves performance for problems requiring deeper thinking upfront." ([Source](https://research.aimultiple.com/agentic-coding/))

**How**: Use two-phase workflow:
1. **Phase 1 (Planning)**:
   - Clarify requirements
   - Research best practices
   - Identify edge cases
   - Propose approach
   - Get approval

2. **Phase 2 (Implementation)**:
   - Write tests (TDD)
   - Implement solution
   - Run tests
   - Document

**Template**: See `.claude/templates/two-phase-prompt.md`

---

### 6. Context Inspection

#### Monitor Token Usage Proactively
**What**: Watch the status bar token percentage throughout session.

**Thresholds**:
- **0-50%**: Green zone - normal operation
- **50-75%**: Yellow zone - start planning exit point
- **75-80%**: Orange zone - wrap up current task and exit
- **80%+**: Red zone - quality degradation likely

**How**:
```bash
# Check context programmatically (if needed)
# Status bar shows: "Tokens: 45,234 / 200,000 (22%)"

# At 75%, wrap up:
You: "Summarize what we've accomplished and update .claude/state/current-state.md"
Claude: (updates state)
You: exit
```

**Research**: "Watch the token percentage in Claude Code's status bar. When you hit 80%, exit the session and restart." ([Source](https://hyperdev.matsuoka.com/p/how-claude-code-got-better-by-protecting))

---

### 7. Security Reviews

#### Manual Review of Generated Code
**What**: Don't auto-accept all changes, especially security-sensitive code.

**Why**: "Agents don't always understand security boundaries - situations have occurred where an agent attempted to add an API_KEY in plain text to a generated README or config file." ([Source](https://research.aimultiple.com/agentic-coding/))

**Review checklist**:
- [ ] No secrets in plain text
- [ ] Input validation present
- [ ] SQL parameterized (no string concatenation)
- [ ] XSS prevention (output escaping)
- [ ] Authentication checked
- [ ] Authorization verified
- [ ] Error messages don't leak sensitive info

---

### 8. Maintaining "Why" Comments

#### Add Context for Future Developers
**What**: Include comments explaining business logic and design decisions.

**Why**: "Code written by agents often lacks the 'why' comments humans include, causing future developers to struggle to understand intent and creating long-term maintenance debt." ([Source](https://research.aimultiple.com/agentic-coding/))

**Good comments**:
```python
# Use exponential backoff to avoid overwhelming API during outages
# (we experienced cascading failures in prod on 2025-03-15)
for attempt in range(max_retries):
    try:
        response = api.call()
        break
    except APIError:
        sleep(2 ** attempt)
```

**Bad comments**:
```python
# Retry on error
for attempt in range(max_retries):
    try:
        response = api.call()
        break
    except APIError:
        sleep(2 ** attempt)
```

---

## 🛠️ Optional Best Practices

### 9. Permission Management

#### Use Allowlists for Safe Tools (Optional)
**What**: Reduce permission prompts for trusted operations.

**Why**: "By default, Claude Code requests permission for actions that might modify your system, which is safe but tedious." ([Source](https://code.claude.com/docs/en/best-practices))

**Options**:
1. **Permission allowlists**: For specific safe tools
2. **Sandboxing**: For OS-level isolation

**How**: See Claude Code settings documentation.

---

### 10. Headless Mode & Automation (Optional)

#### Automate Repetitive Tasks
**What**: Use headless mode for CI/CD integration.

**How**:
```bash
# Run in headless mode:
claude -p "Run tests and report coverage"

# Stream JSON output:
claude -p "Analyze code quality" --output-format stream-json
```

**Note**: Headless mode doesn't persist between sessions.

**Research**: "Use the -p flag with a prompt to enable headless mode, and --output-format stream-json for streaming JSON output." ([Source](https://code.claude.com/docs/en/best-practices))

---

## 📋 Quick Reference Checklist

### Starting New Session
- [ ] Launch from project root: `claude`
- [ ] Claude auto-loads CLAUDE.md and .claude/ files
- [ ] Review `.claude/state/current-state.md` to understand where we are

### During Session
- [ ] Watch token percentage in status bar
- [ ] Use `/clear` when switching topics
- [ ] Use subagents for research tasks
- [ ] Use "think hard" for complex decisions
- [ ] Plan before coding (two-phase workflow)
- [ ] Review security-sensitive changes manually

### Ending Session (at 75-80% context)
- [ ] Update `.claude/state/current-state.md`
- [ ] Add lessons to `.claude/knowledge-base/lessons-learned.md`
- [ ] Document any new tech decisions
- [ ] Exit cleanly: `exit`

### Between Sessions
- [ ] Start fresh when continuing work
- [ ] Claude will remember via .claude/ files
- [ ] No need to repeat context

---

## 🔄 Workflow Examples

### Example 1: Feature Development (Best Practice)

```
Session 1 (Fresh, 0% context):
You: "Add user authentication with JWT. Think hard about security."
Claude: (uses extended thinking)
Claude: (uses subagent for JWT research)
Claude: Proposes plan
You: Approve
Claude: Implements (TDD style)
Claude: Updates .claude/state/current-state.md
Status: 70% context

You: "Good stopping point. Exit."
exit

Session 2 (Fresh, 0% context):
claude
Claude: (auto-reads .claude/state/current-state.md)
Claude: "Last session we implemented JWT auth. Ready to continue with rate limiting?"
You: "Yes, think hard about distributed rate limiting."
...
```

### Example 2: Mixed Tasks (Anti-Pattern)

```
Session 1 (Bad - Kitchen Sink):
You: "Add authentication"
Claude: Works on auth (20% context)
You: "Actually, can you explain how Redis works?"
Claude: Explains Redis (40% context)
You: "OK back to auth, add rate limiting too"
Claude: (confused, context polluted with Redis info)
Status: 60% context, but mixed topics

# Better approach:
You: /clear
You: "Now add rate limiting"
Claude: (clean context for rate limiting)
```

---

## 📊 Performance Impact Data

### Context Management (Research-Based)

**Running to 90% vs Exiting at 75%**:
- 90%: More code per session (quantity)
- 75%: Higher quality, more maintainable code (quality)

**Verdict**: "Sessions that stop at 75% utilization produce less total output but higher-quality, more maintainable code that actually ships." ([Source](https://hyperdev.matsuoka.com/p/how-claude-code-got-better-by-protecting))

**CLAUDE.md Optimization**:
- Before: Full context loaded upfront
- After: 54% reduction in initial context
- Result: More room for work, faster responses, lower costs

([Source](https://gist.github.com/johnlindquist/849b813e76039a908d962b2f0923dc9a))

---

## 🎓 Learning Resources

### Official Documentation
- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)
- [Claude Prompt Engineering Overview](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview)
- [Claude API Docs: Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-4-best-practices)

### Community Resources
- [Arize: CLAUDE.md Best Practices](https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/)
- [Context Optimization Gist](https://gist.github.com/johnlindquist/849b813e76039a908d962b2f0923dc9a)
- [How Claude Code Got Better](https://hyperdev.matsuoka.com/p/how-claude-code-got-better-by-protecting)
- [Optimizing Agentic Coding](https://research.aimultiple.com/agentic-coding/)

---

## 🔄 Updates & Maintenance

This document reflects best practices as of **2026-02-01**. As Claude Code evolves:
- Check official docs quarterly
- Update this file with new findings
- Add to `.claude/knowledge-base/lessons-learned.md` when discovering project-specific patterns

**Next Review**: 2026-05-01

---

*Keep this file updated as new best practices emerge. The template is a living document.*
