# MCPs and Skills (2026)

## Model Context Protocol (MCP)

MCPs are standardized integrations that give AI tools access to external systems.

### When to Use MCPs

- Database access (query, schema inspection)
- API integrations (GitHub, Jira, Slack)
- File system operations (beyond basic read/write)
- External services (search, web scraping)

### MCP Best Practices

1. **Principle of least privilege**: Only enable MCPs needed for current task
2. **Audit MCP usage**: Check what the agent accessed
3. **Prefer built-in tools**: Use native file/exec tools when sufficient
4. **Context considerations**: MCPs add to context window — use judiciously

## Claude Skills

Skills are reusable instruction packages that Claude can apply when a request matches.

### Anatomy of a Skill

```
skills/
├── my-skill/
│   ├── SKILL.md          # Instructions (auto-loaded when triggered)
│   ├── examples/         # Reference implementations
│   └── scripts/          # Helper scripts
```

### When to Create a Skill

- Repeatable workflows (deployments, releases)
- Domain-specific patterns (your company's API style)
- Quality gates (security review, performance audit)
- Team conventions (coding standards, PR format)

### Skill Loading

Skills load **on-demand** when a request matches their description:
- Keep SKILL.md focused on "how", not "what" (description handles "what")
- Include examples for complex procedures
- Reference scripts rather than embedding them

### Community Skills

Useful skill collections:
- [Claude Skills Repo](https://github.com/anthropics/skills) — Official examples
- [x-cmd Skills](https://www.x-cmd.com/skill/) — Community-curated

### Example: Frontend Design Skill

Avoid the "LLM purple" aesthetic:
```
skills/
├── frontend-design/
│   ├── SKILL.md          # "Use modern, clean design. No purple gradients."
│   └── examples/
│       └── style-guide.css
```

## Integration with OpenClaw

OpenClaw loads Skills from:
1. `/opt/homebrew/lib/node_modules/openclaw/skills/` (global)
2. `~/.openclaw/skills/` (user)
3. Project `.claude/skills/` (project-specific)

Match skills by checking `<available_skills>` in system prompt.
