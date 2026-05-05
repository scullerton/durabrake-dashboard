#!/bin/zsh
# Uninstall the Mac launchd backlog snapshot job.
# Removes the launchd registration, the plist copy in LaunchAgents,
# and prints the command to clear the pmset wake schedule.
#
# Does NOT remove:
#   - ~/.durabrake-venv (the Python venv) — harmless if left
#   - logs/ (kept for auditing)

set -euo pipefail

PLIST_LABEL="com.durabrake.backlog-snapshot"
PLIST_DST="$HOME/Library/LaunchAgents/com.durabrake.backlog.plist"
GUI_TARGET="gui/$(id -u)"

echo "▶ Uninstalling DuraBrake backlog snapshot launchd job"
echo ""

# 1. Bootout (unload) the running job, ignoring "not loaded" errors
if launchctl print "$GUI_TARGET/$PLIST_LABEL" >/dev/null 2>&1; then
    launchctl bootout "$GUI_TARGET/$PLIST_LABEL"
    echo "  ✓ launchd job unloaded"
else
    echo "  · launchd job was not loaded (skipping)"
fi

# 2. Remove the plist file
if [ -f "$PLIST_DST" ]; then
    rm "$PLIST_DST"
    echo "  ✓ removed $PLIST_DST"
else
    echo "  · no plist at $PLIST_DST (already gone)"
fi

echo ""
echo "──────────────────────────────────────────────────────────────────"
echo "  To stop the nightly Mac wake (also requires sudo):"
echo ""
echo "      sudo pmset repeat cancel"
echo ""
echo "──────────────────────────────────────────────────────────────────"
