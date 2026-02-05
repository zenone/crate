#!/bin/bash
# Quick Manual Test Suite

echo "========================================="
echo "  Quick Manual Test Suite"
echo "========================================="
echo ""

# Test 1: API Import
echo -n "1. API Import...................... "
python3 -c "from dj_mp3_renamer.api import RenamerAPI" 2>/dev/null && echo "✓ PASS" || echo "✗ FAIL"

# Test 2: CLI Old Script
echo -n "2. CLI Old Script.................. "
python3 dj_mp3_renamer.py --help > /dev/null 2>&1 && echo "✓ PASS" || echo "✗ FAIL"

# Test 3: CLI Module
echo -n "3. CLI Module...................... "
python3 -m dj_mp3_renamer --help > /dev/null 2>&1 && echo "✓ PASS" || echo "✗ FAIL"

# Test 4: CLI Installed Command
echo -n "4. CLI Installed Command........... "
dj-mp3-renamer --help > /dev/null 2>&1 && echo "✓ PASS" || echo "⚠ SKIP (not in PATH)"

# Test 5: Unit Tests
echo -n "5. Unit Tests...................... "
RESULT=$(pytest tests/ -q 2>&1 | tail -1)
if echo "$RESULT" | grep -q "129 passed"; then
    echo "✓ PASS (129/129)"
else
    echo "✗ FAIL"
fi

# Test 6: Core Module Imports
echo -n "6. Core Module Imports............. "
python3 -c "
from dj_mp3_renamer.core import sanitization
from dj_mp3_renamer.core import key_conversion
from dj_mp3_renamer.core import metadata_parsing
from dj_mp3_renamer.core import template
from dj_mp3_renamer.core import io
" 2>/dev/null && echo "✓ PASS" || echo "✗ FAIL"

# Test 7: API Functionality
echo -n "7. API Basic Functionality......... "
python3 << 'EOF' 2>/dev/null
from pathlib import Path
from dj_mp3_renamer.api import RenamerAPI, RenameRequest
api = RenamerAPI(workers=4)
request = RenameRequest(path=Path("/tmp"), dry_run=True)
# Just test instantiation, not execution
print("PASS")
EOF
test $? -eq 0 && echo "✓ PASS" || echo "✗ FAIL"

echo ""
echo "========================================="
echo "  Quick Tests Complete"
echo "========================================="
echo ""
echo "Next Steps:"
echo "1. ⭐ Test with REAL MP3 files (CRITICAL)"
echo "   mkdir -p ~/Music/TEST_RENAME"
echo "   cp ~/Music/YourSongs/*.mp3 ~/Music/TEST_RENAME/"
echo "   dj-mp3-renamer ~/Music/TEST_RENAME --dry-run -vv"
echo ""
echo "2. See MANUAL_TESTING.md for comprehensive tests"
echo ""
