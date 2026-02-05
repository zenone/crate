# Tech Stack Decisions

**Purpose**: Document every technology choice, the alternatives considered, and the rationale. This prevents "why did we choose X?" questions later and helps with future upgrades.

**Format**: Each decision should include date, options evaluated, final choice, rationale, and trade-offs.

---

## How to Use This File

### When to Add an Entry
- Choosing programming language
- Selecting framework or library
- Picking database or storage solution
- Choosing deployment platform
- Selecting testing framework
- Any technology with multiple viable options

### Decision Template
```markdown
## [YYYY-MM-DD] [Category]: [Technology Name]

**Decision**: We chose [X]

**Context**: What problem were we solving?

**Options Evaluated**:
1. **[Option A]**
   - Pros: ...
   - Cons: ...
   - Research: [links to docs, Stack Overflow, comparisons]

2. **[Option B]**
   - Pros: ...
   - Cons: ...
   - Research: [links]

**Rationale**: Why we chose this option

**Trade-offs**: What we gave up by not choosing alternatives

**Success Metrics**: How we'll know if this was the right choice

**Review Date**: When to reconsider (e.g., 1 year from now)

**Tags**: #backend #frontend #database #devops
```

---

## Decisions Log

### Template Project Stack

#### [2026-02-01] Documentation System: CLAUDE.md + .claude/ Directory

**Decision**: Use native Claude Code CLAUDE.md + .claude/ structure

**Context**: Need persistent memory across Claude sessions with automatic loading

**Options Evaluated**:
1. **CLAUDE.md + .claude/ (Native)**
   - Pros: Officially supported, auto-loaded by Claude, hierarchical (global/project/local)
   - Cons: Requires discipline to keep updated
   - Research: https://code.claude.com/docs/en/memory

2. **Third-party MCP (Basic Memory)**
   - Pros: More advanced persistence features
   - Cons: Additional setup, external dependency
   - Research: https://docs.basicmemory.com/integrations/claude-code/

3. **Custom Solution (Database)**
   - Pros: Complete control
   - Cons: Significant overhead, not auto-loaded by Claude

**Rationale**:
- Native solution requires zero setup
- Claude automatically reads on startup
- Version controllable (team collaboration)
- Proven pattern from official docs

**Trade-offs**:
- Requires manual updates (not automatic)
- Limited to text files (no rich querying)

**Success Metrics**:
- Context preserved across sessions (subjective)
- No repeated mistakes (check lessons-learned.md growth)

**Tags**: #meta #documentation #persistence

---

## Research Methodology

When evaluating new technologies, follow this process:

### 1. Web Search (Current Best Practices)
```
Search: "best [technology category] 2026"
Search: "[specific use case] [technology] 2026"
Search: "[technology A] vs [technology B] 2026"
```

### 2. Check Community Health
- GitHub: Stars, forks, last commit date, open issues
- Stack Overflow: Question volume, answer quality
- Reddit/HackerNews: Recent discussions
- Official docs: Quality, completeness, examples

### 3. Evaluate Against Criteria
- **Performance**: Benchmarks, real-world usage
- **Security**: CVE history, audit reports, update frequency
- **Developer Experience**: Learning curve, debugging tools, error messages
- **Community Support**: Active maintainers, quick issue response
- **Longevity**: Company backing, adoption rate, migration path

### 4. Proof of Concept
- Build small test project
- Measure setup time
- Identify gotchas
- Check integration with existing stack

### 5. Document Decision
- Add entry to this file
- Include all research links
- Document trade-offs honestly
- Set review date

---

## Stack by Category

### Language
- **Choice**: [To be determined per project]
- **Research Date**: -
- **Entry**: [Link to detailed entry when decided]

### Backend Framework
- **Choice**: [To be determined]
- **Research Date**: -
- **Entry**: [Link]

### Frontend Framework
- **Choice**: [To be determined]
- **Research Date**: -
- **Entry**: [Link]

### Database
- **Choice**: [To be determined]
- **Research Date**: -
- **Entry**: [Link]

### API Design
- **Choice**: OpenAPI/Swagger (recommended for API-first architecture)
- **Research Date**: 2026-02-01
- **Entry**: See API documentation standards below

### Testing Framework
- **Choice**: [To be determined per language]
- **Research Date**: -
- **Entry**: [Link]

### Deployment Platform
- **Choice**: [To be determined]
- **Research Date**: -
- **Entry**: [Link]

---

## API Documentation Standard

### [2026-02-01] API Documentation: OpenAPI/Swagger

**Decision**: Use OpenAPI 3.1 specification with Swagger UI

**Context**: API-first architecture requires machine-readable API contracts

**Options Evaluated**:
1. **OpenAPI/Swagger**
   - Pros: Industry standard, code generation, interactive docs, wide tooling support
   - Cons: Requires keeping spec in sync with code
   - Research: https://swagger.io/specification/

2. **API Blueprint**
   - Pros: Human-readable Markdown format
   - Cons: Less tooling support, smaller community

3. **RAML**
   - Pros: YAML-based, good for design-first
   - Cons: Declining adoption, fewer tools

**Rationale**:
- OpenAPI is industry standard (2026)
- Best tooling ecosystem
- Supports code generation (client SDKs, server stubs)
- Interactive documentation with Swagger UI
- Validation tools available

**Implementation**:
- Define API contract in `openapi.yaml` before implementing
- Use tools: Swagger Editor (design), Swagger Codegen (generate), Swagger UI (docs)
- Validate spec as part of CI/CD

**Tags**: #api #documentation #tooling

---

## Deprecated/Rejected Technologies

### Technologies We Explicitly Avoid

#### [Technology Name]
**Why**: [Reason for rejection]
**Alternatives**: [What to use instead]
**Last Reviewed**: [Date]

---

## Review Schedule

- **Quarterly Review**: Check for major updates to dependencies
- **Annual Review**: Reconsider core technology choices
- **On Incident**: If production issue related to technology choice, review decision

---

## Statistics

- **Total Decisions Documented**: 2
- **Last Updated**: 2026-02-01
- **Next Review**: 2027-02-01

---

*Keep this file current. Future you (and your team) will thank present you for the documentation.*
