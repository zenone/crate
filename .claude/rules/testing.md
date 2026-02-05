# Testing Rules

## TDD: Red → Green → Refactor
1. **Red**: Write failing test first
2. **Green**: Write minimum code to pass
3. **Refactor**: Clean up while keeping tests green

## Test Naming
```python
def test_<unit>_<scenario>_<expected>():
    """Example: test_login_with_invalid_password_returns_401"""
```

## Test Structure (Arrange-Act-Assert)
```python
def test_user_login_with_valid_credentials_returns_token():
    # Arrange
    user = create_test_user(password="secret123")
    
    # Act
    result = auth.login("testuser", "secret123")
    
    # Assert
    assert result.token is not None
    assert result.expires_in == 3600
```

## What to Test

### Always Test
- Happy path (expected inputs → expected outputs)
- Edge cases (empty, null, boundary values)
- Error cases (invalid input, missing resources)
- Security-sensitive code (auth, input validation)

### Skip Testing
- Framework internals (trust your dependencies)
- Trivial getters/setters
- Generated code
- Third-party library behavior

## Test Isolation
- Each test must be independent (no shared state)
- Use fixtures/factories for test data
- Clean up after tests (or use transactions)
- Mock external services (APIs, databases in unit tests)

## Coverage Guidelines
- Aim for 80%+ on business logic (`api/`, `core/`)
- Don't chase 100% (diminishing returns)
- 0% coverage on UI layers is OK if integration tests exist

## Test Speed
- Unit tests: < 100ms each
- Integration tests: < 1s each
- Slow tests → mark and run separately

## When Tests Fail
1. Read the error message carefully
2. Check if test is correct (not implementation)
3. Run test in isolation: `pytest path/to/test.py::test_name -v`
4. Add debugging: `pytest --pdb` or print statements
5. Fix implementation, not test (unless test is wrong)

## Flaky Tests
- Flaky test = test that sometimes passes, sometimes fails
- **Fix immediately** or delete — flaky tests erode trust
- Common causes: time-dependent, shared state, race conditions
