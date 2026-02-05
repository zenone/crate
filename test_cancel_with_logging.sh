#!/bin/bash
#
# Test Cancel Button with Debug Logging
#
# This script launches the TUI with verbose logging to help diagnose
# why the cancel button isn't working.
#

cd "$(dirname "$0")"

echo "=========================================="
echo "CANCEL BUTTON DEBUG TEST"
echo "=========================================="
echo ""
echo "Instructions:"
echo "  1. The TUI will launch with debug logging enabled"
echo "  2. Select a directory with many MP3 files"
echo "  3. Click Preview (P)"
echo "  4. IMMEDIATELY click Cancel (C) or press the C key"
echo "  5. Watch the terminal output for debug messages"
echo ""
echo "Look for these messages:"
echo "  - 🖱️  CANCEL BUTTON CLICKED"
echo "  - ⚠️  CANCELLATION DETECTED"
echo "  - ⚠️  CANCELLATION EXCEPTION CAUGHT"
echo ""
echo "If you DON'T see these messages, the cancel isn't being detected."
echo "Press ENTER to continue..."
read

# Run with debug logging
python3 ./run_tui.py --dev 2>&1 | tee /tmp/cancel_debug.log

echo ""
echo "=========================================="
echo "Debug log saved to: /tmp/cancel_debug.log"
echo "=========================================="
