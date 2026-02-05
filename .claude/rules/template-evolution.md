# Template Evolution

How AI should improve ai-dev-kit itself based on real-world experience.

---

## The Meta-Learning Loop

```
Use template → Learn lesson → Improve template → Better future projects
```

AI should not just capture lessons for the current project—it should also consider whether the lesson applies to **all future projects** using this template.

---

## When to Evolve the Template

### Definitely Update Template When:
- A pattern worked well and should be standard
- A common mistake keeps happening (add prevention guidance)
- A tool/command is useful across all projects
- A workflow step is missing or unclear
- Research reveals new best practices

### Don't Update Template When:
- Lesson is project-specific (put in project's lessons-learned.md)
- Change is experimental (test in one project first)
- You're unsure if it generalizes

---

## Evolution Workflow

### Step 1: Identify Template-Worthy Lesson

Ask yourself:
```
"Would this help EVERY project using ai-dev-kit, or just this one?"
```

If yes → proceed to update template.
If no → add to project's `.claude/knowledge-base/lessons-learned.md` instead.

### Step 2: Pull Latest Template

**Always pull before modifying** to avoid conflicts:

```bash
cd ~/Code/tools/ai-dev-kit
git pull origin main
```

### Step 3: Make the Change

Modify the appropriate file:

| Type of Lesson | Where to Add |
|----------------|--------------|
| New rule/guideline | `.claude/rules/[topic].md` |
| New pattern | `.claude/knowledge-base/[type]-patterns.md` |
| New workflow | `.claude/workflows/[name].md` |
| New template/checklist | `.claude/templates/[name].md` |
| Tool reference | `.claude/rules/code-quality-tools.md` |

### Step 4: Commit with Clear Message

```bash
git add -A
git commit -m "feat: Add [what] based on [project] learnings

- [Specific improvement]
- [Why it matters]
- [Example use case]"
```

### Step 5: Push to Share

```bash
git push origin main
```

Now all future projects (and other machines) benefit.

---

## What to Document in Template Updates

### For New Rules
```markdown
# [Rule Name]

## When to Apply
[Clear trigger conditions]

## The Rule
[Concise, actionable guidance]

## Examples
[Good and bad examples]

## Why This Matters
[Motivation from real experience]
```

### For New Patterns
```markdown
## [Pattern Name]

**When**: [Situation this applies to]

**Pattern**:
[Code/structure/process]

**Why**: [Real-world motivation]

**Example**: [From actual project]
```

---

## Template vs Project Lessons

| Lesson Type | Where It Goes |
|-------------|---------------|
| "Always use bcrypt for passwords" | Template (`security.md`) |
| "Our API uses Bearer tokens" | Project (tech-stack-decisions.md) |
| "Vulture finds dead code effectively" | Template (`dead-code.md`) |
| "The /users endpoint expects ISO dates" | Project (lessons-learned.md) |
| "Exit at 75% context window" | Template (`context-management.md`) |
| "Redis cache TTL should be 5 minutes" | Project (tech-stack-decisions.md) |

---

## Cross-Machine Template Sync

If using ai-dev-kit across multiple machines:

### On Machine That Learned Something
```bash
cd ~/Code/tools/ai-dev-kit
git add -A
git commit -m "feat: [improvement]"
git push
```

### On Other Machines
```bash
cd ~/Code/tools/ai-dev-kit
git pull
```

Consider a periodic sync reminder in heartbeats.

---

## Quality Gate for Template Changes

Before committing template changes:

- [ ] Is this lesson general (applies to all projects)?
- [ ] Is the guidance clear and actionable?
- [ ] Are there examples?
- [ ] Does it conflict with existing guidance?
- [ ] Did you pull latest first?

---

## Anti-Patterns

❌ **Project-specific in template**: "Use PostgreSQL" (not all projects need this)

❌ **Forgetting to pull**: Making changes to stale version → merge conflicts

❌ **Vague lessons**: "Be careful with auth" (not actionable)

❌ **Not pushing**: Learning something valuable but not sharing it

❌ **Over-engineering**: Adding complex processes for rare edge cases

---

## Prompt for AI Self-Improvement

When AI discovers something valuable:

```
"This lesson seems like it would help all future projects. 

Before adding to ai-dev-kit:
1. cd ~/Code/tools/ai-dev-kit && git pull
2. Identify the right file to update
3. Make a clear, actionable addition
4. Commit with descriptive message
5. Push to share

Should I update the template with this lesson?"
```
