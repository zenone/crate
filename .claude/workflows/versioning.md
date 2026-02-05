# Versioning Guide

## Semantic Versioning (SemVer)

Format: **MAJOR.MINOR.PATCH** (e.g., `2.1.3`)

| Bump  | When                                    | Example                          |
|-------|-----------------------------------------|----------------------------------|
| MAJOR | Breaking changes                        | Removed API, changed behavior    |
| MINOR | New features (backward compatible)      | Added endpoint, new CLI flag     |
| PATCH | Bug fixes (backward compatible)         | Fixed crash, corrected output    |

## Pre-release Versions

```
1.0.0-alpha.1   # Early testing, unstable
1.0.0-beta.1    # Feature complete, testing
1.0.0-rc.1      # Release candidate, final testing
1.0.0           # Stable release
```

## Version Bumping Workflow

### 1. Determine Version Type
- Ask: "Will this break existing users?"
  - Yes → MAJOR
  - No, but adds features → MINOR  
  - No, just fixes → PATCH

### 2. Update Version in Code
```bash
# Python (pyproject.toml)
version = "2.1.0"

# Node (package.json)
"version": "2.1.0"

# Manual constant
__version__ = "2.1.0"
```

### 3. Update CHANGELOG.md
```markdown
## [2.1.0] - 2026-02-04

### Added
- New feature X

### Fixed
- Bug in Y
```

### 4. Commit & Tag
```bash
git add -A
git commit -m "chore: release v2.1.0"
git tag -a v2.1.0 -m "Release v2.1.0"
git push && git push --tags
```

### 5. Create GitHub Release
```bash
gh release create v2.1.0 --title "v2.1.0" --notes-file CHANGELOG_EXCERPT.md
```

## Breaking Change Checklist

Before bumping MAJOR:
- [ ] Document migration path
- [ ] Update README with breaking changes
- [ ] Consider deprecation period (warn in MINOR, remove in MAJOR)
- [ ] Update all examples and docs

## Version in Code

```python
# src/myapp/__init__.py
__version__ = "2.1.0"

def get_version() -> str:
    return __version__
```

```typescript
// src/version.ts
export const VERSION = "2.1.0";
```

## When to Release

- **PATCH**: As soon as bug is fixed and tested
- **MINOR**: When feature is complete and documented
- **MAJOR**: Plan release date, communicate to users

## 0.x.y Versions

During initial development (`0.x.y`):
- API is unstable
- MINOR can include breaking changes
- Graduate to `1.0.0` when API is stable
