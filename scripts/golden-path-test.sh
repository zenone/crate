#!/usr/bin/env bash
#
# Golden Path Test Runner for Crate
#
# Runs automated golden-path tests against real MP3 files.
# Uses the smoke test fixture at /Users/szenone/Music/DJ/CrateSmokeTest
#
# Usage:
#   ./scripts/golden-path-test.sh          # Run all golden path tests
#   ./scripts/golden-path-test.sh quick    # Run quick preview-only test
#   ./scripts/golden-path-test.sh verbose  # Run with full output
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

FIXTURE_PATH="/Users/szenone/Music/DJ/CrateSmokeTest"

echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Crate Golden Path Test Runner        ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

# Check fixture exists
if [[ ! -d "$FIXTURE_PATH" ]]; then
    echo -e "${RED}✗ Smoke test fixture not found: $FIXTURE_PATH${NC}"
    echo "  Please ensure the fixture directory exists with MP3 files."
    exit 1
fi

mp3_count=$(find "$FIXTURE_PATH" -name "*.mp3" | wc -l | tr -d ' ')
echo -e "${GREEN}✓${NC} Found fixture: $FIXTURE_PATH ($mp3_count MP3 files)"

# Activate venv if exists
if [[ -d ".venv" ]]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
    echo -e "${GREEN}✓${NC} Activated virtual environment"
fi

# Parse arguments
MODE="${1:-full}"

case "$MODE" in
    quick)
        echo -e "\n${YELLOW}Running quick preview tests only...${NC}\n"
        pytest tests/test_golden_path.py -v -k "preview" --tb=short -q
        ;;
    verbose)
        echo -e "\n${YELLOW}Running full suite with verbose output...${NC}\n"
        pytest tests/test_golden_path.py -v --tb=long -s
        ;;
    full|*)
        echo -e "\n${YELLOW}Running full golden path test suite...${NC}\n"
        pytest tests/test_golden_path.py -v --tb=short
        ;;
esac

exit_code=$?

echo ""
if [[ $exit_code -eq 0 ]]; then
    echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║        All golden path tests passed!     ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
else
    echo -e "${RED}╔══════════════════════════════════════════╗${NC}"
    echo -e "${RED}║        Some golden path tests failed     ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════╝${NC}"
fi

exit $exit_code
