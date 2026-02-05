#!/bin/bash
#
# DEBUG CANCEL BUTTON - See what's actually happening
#

echo "=================================================="
echo "CANCEL BUTTON DEBUG MODE"
echo "=================================================="
echo ""
echo "When you click Cancel or press C, you should see:"
echo "  🖱️  CANCEL BUTTON CLICKED"
echo "  or"
echo "  ⌨️  'C' KEY PRESSED"
echo ""
echo "Then you should see:"
echo "  ⚠️  CANCELLATION DETECTED"
echo ""
echo "If you DON'T see these, the cancel isn't working."
echo ""
echo "Press ENTER to launch TUI..."
read

cd "$(dirname "$0")"

# Run with stderr visible
python3 ./run_tui.py 2>&1
