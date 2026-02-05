# Security Rules

## Secrets & Configuration
- No secrets in repo: tokens, keys, passwords.
- Use `.env.example` + env vars.
- Validate inputs at boundaries.
- When adding dependencies, consider supply-chain risk and keep them minimal.

## macOS TCC (Transparency, Consent, and Control)
On macOS, **root cannot access user files** protected by TCC:
- `~/.profile`, `~/.zshrc`, `~/.gitconfig`, `~/Documents/`, etc.
- Symptom: "Operation not permitted" despite running as root
- **Fix**: Check file accessibility before reading; provide graceful fallbacks
- **Pattern**: Don't assume elevated privileges grant access to user data

## Privileged Operations Pattern
For apps needing sudo/root operations (system maintenance, daemons, etc.):

```
┌─────────────┐     writes job     ┌──────────────────┐
│  Web/CLI    │ ───────────────► │  Job Queue Dir   │
│  (user)     │                   │  /var/local/app/ │
└─────────────┘                   └────────┬─────────┘
                                           │ watches
                                  ┌────────▼─────────┐
                                  │   Root Daemon    │
                                  │  (LaunchDaemon)  │
                                  └──────────────────┘
```

- User-facing app writes job files to shared directory
- Root daemon watches queue, executes privileged operations
- Result: No password prompts in UI, clean privilege separation

## Preview Mode for Destructive Operations
Any operation that deletes/modifies data should have a preview mode:
- `--preview` or `--dry-run` flag shows what would happen
- Same code path, just skip the `execute()` call
- UX win: Users trust tools that let them look before leaping

## Error Messages
- Don't leak sensitive info (paths, usernames, internal IDs)
- Log full details to file; show sanitized message to user
