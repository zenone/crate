# Systematic Reasoning Rules

## When to Apply Structured Reasoning

Use explicit step-by-step reasoning for:
- Architecture decisions
- Complex algorithms or data transformations
- Security-sensitive code
- Performance-critical paths
- Bug diagnosis (especially when cause is unclear)
- Any change touching 3+ files

## Reasoning Format

For each significant step, capture:
```
Step N: [Action]
- Reasoning: [Why this step is necessary]
- Result: [What this produces]
- Next: [How this connects to the following step]
```

## Internal vs External Reasoning

**Internal (silent)**: Use extended thinking (`think`, `think hard`, `ultrathink`) for:
- Evaluating tradeoffs
- Security implications
- Edge case analysis
- Design pattern selection

**External (visible)**: Show step-by-step reasoning when:
- Making architecture decisions (human needs to approve)
- Debugging complex issues (paper trail helps)
- Asked explicitly ("walk me through your reasoning")

## Connecting Steps

Never leave steps isolated. Each step should:
1. Reference what it builds on (if applicable)
2. State what it produces
3. Explain why the next step depends on this one

**Example**:
```
Step 1: Define data model
- Reasoning: API contract depends on data shape; define this first
- Result: User model with id, email, password_hash fields
- Next: Step 2 will use this model for the API endpoint

Step 2: Create API endpoint
- Reasoning: Builds on User model from Step 1; clients need this to authenticate
- Result: POST /api/v1/login accepting email+password, returning JWT
- Next: Step 3 implements the business logic this endpoint calls
```

## Problem Decomposition

For complex problems:
1. **State the goal** clearly (what does success look like?)
2. **Identify constraints** (time, security, compatibility, dependencies)
3. **Break into subproblems** (each should be independently testable)
4. **Order by dependency** (what must be done before what?)
5. **Execute sequentially** (one step at a time, verify before moving on)

## When to Pause and Re-plan

Stop and reconsider if:
- Step N fails in an unexpected way
- New information changes earlier assumptions
- Context window approaching 75%
- Complexity exceeds initial estimate (scope creep)

Document the re-plan in `.claude/state/current-state.md`.
