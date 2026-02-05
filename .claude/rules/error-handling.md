# Error Handling Rules

## Fail Fast, Fail Clearly
- Validate inputs at boundaries (API entry, CLI args, config load)
- Raise exceptions early; don't propagate bad state
- Include context in error messages: what failed, why, what to do

## Error Message Format
```
[Component] Action failed: <reason>
  Context: <relevant details>
  Fix: <actionable suggestion>
```

**Good**: `[Auth] Login failed: invalid credentials for user 'john@example.com'. Fix: Check password or reset via /forgot-password`

**Bad**: `Error: something went wrong`

## Exception Hierarchy
```python
class AppError(Exception):
    """Base for all app errors (catchable as group)."""

class ValidationError(AppError):
    """Invalid input from user."""

class ConfigError(AppError):
    """Missing or invalid configuration."""

class ExternalServiceError(AppError):
    """Third-party API/service failure."""
```

## Logging vs Raising
- **Log + continue**: Transient issues, retryable operations
- **Raise**: Unrecoverable errors, invalid state, security violations
- **Log + raise**: When you need audit trail AND must stop

## User-Facing vs Internal
- **User-facing**: Sanitized, actionable, no internal paths/IDs
- **Internal logs**: Full stack trace, context, timestamps

## Retry Strategy
```python
for attempt in range(max_retries):
    try:
        return api.call()
    except TransientError:
        if attempt == max_retries - 1:
            raise
        sleep(2 ** attempt)  # Exponential backoff
```

## Never Swallow Exceptions
```python
# ❌ Bad
try:
    risky_operation()
except Exception:
    pass  # Silent failure

# ✅ Good
try:
    risky_operation()
except SpecificError as e:
    logger.warning(f"Operation failed, using fallback: {e}")
    return fallback_value
```
