# Knowledge Base

This directory contains documentation of lessons learned, coding standards, and best practices for the DJ MP3 Renamer project.

## Files

### [lessons-learned.md](./lessons-learned.md)
Comprehensive documentation of:
- Architecture patterns (API-First, Progressive Loading)
- Web development best practices
- Server management solutions
- Error handling strategies
- UI/UX patterns
- Common pitfalls and solutions
- Performance considerations
- Development workflow

**When to reference**:
- Before starting new features
- When encountering similar problems
- During code reviews
- When onboarding new developers

### [coding-standards.md](./coding-standards.md)
Code style guidelines and conventions for:
- Python code standards (PEP 8, type hints, docstrings)
- JavaScript code standards (ES6+, async/await)
- CSS code standards (naming, organization, variables)
- HTML code standards (semantic HTML, accessibility)
- API design standards (REST, request/response models)
- Testing standards (naming, structure, fixtures)
- Git standards (branching, commits, what to commit)
- Documentation standards (comments, READMEs)
- Performance guidelines
- Security guidelines

**When to reference**:
- Before writing code
- During code reviews
- When setting up linters/formatters
- When writing tests

## Core Principles

This project follows two fundamental principles:

### 1. API-First Architecture
Build backend APIs first, then connect frontend UIs.

**Benefits**:
- Decouples frontend and backend
- Enables multiple clients (web, CLI, TUI)
- Makes testing easier
- Allows parallel development

**Implementation**:
- `RenamerAPI` class provides core functionality
- FastAPI endpoints wrap `RenamerAPI` methods
- Frontend uses API client for all operations
- All data validated with Pydantic models

### 2. Test-Driven Development (TDD)
Write tests before implementing features.

**Process**:
1. Write failing test
2. Implement minimum code to pass
3. Refactor while keeping tests green
4. Repeat

**Benefits**:
- Forces clear API design
- Prevents over-engineering
- Catches regressions immediately
- Makes refactoring safe

**Status**: 285 tests passing, 100% coverage

## Quick Reference

**Start web UI**: `./start_web_ui.sh`
**Stop web UI**: `./stop_web_ui.sh`
**Run tests**: `pytest tests/ -v --cov`
**View API docs**: http://localhost:8000/docs (when server running)

## Contributing

When contributing to this project:

1. **Read lessons-learned.md** to understand project history and avoid known pitfalls
2. **Follow coding-standards.md** for consistent code style
3. **Write tests first** (TDD approach)
4. **Build APIs first** (API-First approach)
5. **Update this knowledge base** when discovering new patterns or solutions

## Adding New Documentation

When you learn something valuable:

1. **Update lessons-learned.md** with:
   - What problem you encountered
   - How you solved it
   - Why the solution works
   - Code examples if applicable

2. **Update coding-standards.md** if:
   - You establish a new pattern
   - You find a better way to do something
   - You add new tools/dependencies

3. **Update this README** if:
   - You add new documentation files
   - You change the structure

## Maintenance

This knowledge base should be:
- **Updated frequently** - After completing major features or fixing significant bugs
- **Reviewed regularly** - During sprint retrospectives
- **Referenced consistently** - In code reviews and planning sessions
- **Version controlled** - Committed with code changes

**Last Updated**: 2026-01-29
**Maintainer**: szenone + Claude Sonnet 4.5
