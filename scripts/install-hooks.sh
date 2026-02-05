#!/usr/bin/env bash
set -euo pipefail

# scripts/install-hooks.sh
# Set up git hooks and pre-commit for quality automation

echo "🔧 Setting up git hooks..."

# Check for pre-commit
if command -v pre-commit >/dev/null 2>&1; then
    echo "✓ pre-commit found"
    
    if [ -f ".pre-commit-config.yaml" ]; then
        echo "Installing pre-commit hooks..."
        pre-commit install
        echo "✓ pre-commit hooks installed"
        
        echo ""
        echo "Running pre-commit on all files (first-time setup)..."
        pre-commit run --all-files || true
        echo "✓ Initial check complete"
    else
        echo "⚠️  No .pre-commit-config.yaml found"
        echo "   Copy from template: cp /path/to/template/.pre-commit-config.yaml ."
    fi
else
    echo "⚠️  pre-commit not found"
    echo "   Install with: pip install pre-commit"
    echo "   Or: brew install pre-commit"
fi

# Set up commit-msg hook for conventional commits (optional)
HOOKS_DIR=".git/hooks"
if [ -d "$HOOKS_DIR" ]; then
    cat > "$HOOKS_DIR/commit-msg" << 'HOOK'
#!/bin/sh
# Enforce conventional commit format (optional)
# Types: feat, fix, docs, style, refactor, test, chore

commit_msg=$(cat "$1")
pattern="^(feat|fix|docs|style|refactor|test|chore|improve|remove)(\(.+\))?: .{1,72}"

if ! echo "$commit_msg" | grep -qE "$pattern"; then
    echo "❌ Commit message doesn't follow conventional format:"
    echo "   <type>: <description>"
    echo ""
    echo "   Types: feat, fix, docs, style, refactor, test, chore, improve, remove"
    echo "   Example: feat: add user authentication"
    echo ""
    echo "   Your message: $commit_msg"
    exit 1
fi
HOOK
    chmod +x "$HOOKS_DIR/commit-msg"
    echo "✓ Conventional commit hook installed"
fi

echo ""
echo "🎉 Git hooks setup complete!"
echo ""
echo "Hooks installed:"
echo "  - pre-commit: Runs linters, formatters, security checks"
echo "  - commit-msg: Enforces conventional commit format"
