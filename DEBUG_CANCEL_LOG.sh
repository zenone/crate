#!/bin/bash
#
# DEBUG CANCEL BUTTON - With stderr logging to file
#

LOGFILE="/tmp/cancel_debug.log"

echo "==================================================" | tee "$LOGFILE"
echo "CANCEL BUTTON DEBUG MODE (Logging to $LOGFILE)" | tee -a "$LOGFILE"
echo "==================================================" | tee -a "$LOGFILE"
echo "" | tee -a "$LOGFILE"
echo "When you click Cancel or press C, check $LOGFILE for:" | tee -a "$LOGFILE"
echo "  🖱️  CANCEL BUTTON CLICKED" | tee -a "$LOGFILE"
echo "  or" | tee -a "$LOGFILE"
echo "  ⌨️  'C' KEY PRESSED" | tee -a "$LOGFILE"
echo "" | tee -a "$LOGFILE"
echo "Press ENTER to launch TUI..." | tee -a "$LOGFILE"
read

cd "$(dirname "$0")"

# Run with stderr redirected to log file
python3 ./run_tui.py 2>>"$LOGFILE"

echo "" | tee -a "$LOGFILE"
echo "==================================================" | tee -a "$LOGFILE"
echo "TUI closed. Showing last 50 lines of log:" | tee -a "$LOGFILE"
echo "==================================================" | tee -a "$LOGFILE"
tail -50 "$LOGFILE"
