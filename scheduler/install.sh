#!/bin/zsh
# One-time installer for the Mac launchd backlog snapshot job.
#
# Idempotent — safe to re-run after edits to the plist or job_a.sh.
#
# Architecture decision: the source-of-truth wrapper script lives in Box
# (scheduler/job_a.sh), but launchd reads its installed copy from
# ~/Library/Application Support/DuraBrakeDashboard/. That's because
# macOS TCC sandboxes launchd jobs and blocks reads from
# ~/Library/CloudStorage/ without an explicit privacy grant. The
# Application Support path is unrestricted, so the system "just works"
# without any user-facing TCC prompts.

set -euo pipefail

PROJECT_ROOT="/Users/sculls/Library/CloudStorage/Box-Box/DuraParts/Finance/KPI Dashboard"
SCHEDULER_DIR="$PROJECT_ROOT/scheduler"
PLIST_LABEL="com.durabrake.backlog-snapshot"
PLIST_DST="$HOME/Library/LaunchAgents/com.durabrake.backlog.plist"
LOG_DIR="$PROJECT_ROOT/logs"

# Where to install the wrapper script (outside CloudStorage = no TCC issues)
APP_SUPPORT="$HOME/Library/Application Support/DuraBrakeDashboard"
JOB_A_INSTALLED="$APP_SUPPORT/job_a.sh"

echo "▶ Installing DuraBrake backlog snapshot launchd job"
echo ""

# 1. Install the wrapper to App Support (outside CloudStorage)
mkdir -p "$APP_SUPPORT"
cp "$SCHEDULER_DIR/job_a.sh" "$JOB_A_INSTALLED"
chmod +x "$JOB_A_INSTALLED"
echo "  ✓ wrapper copied to $JOB_A_INSTALLED"

# 2. Ensure log directory exists (plist references it)
mkdir -p "$LOG_DIR"
echo "  ✓ logs/ exists"

# 3. Bootstrap venv proactively (so the first launchd-triggered run isn't
#    slowed down by ~30s of pip installs at 23:45). Uses Homebrew Python
#    3.10+ — system /usr/bin/python3 (3.9) lacks str | None syntax.
VENV_DIR="$HOME/.durabrake-venv"
if [ ! -x "$VENV_DIR/bin/python3" ] || ! "$VENV_DIR/bin/python3" -c 'import keyring, requests, pandas, openpyxl' 2>/dev/null; then
    echo "  ▶ Bootstrapping venv at $VENV_DIR..."

    PYTHON_BOOTSTRAP=""
    for candidate in /opt/homebrew/bin/python3 /usr/local/bin/python3; do
        if [ -x "$candidate" ]; then
            ver="$("$candidate" -c 'import sys; print(sys.version_info.major*100+sys.version_info.minor)')"
            if [ "$ver" -ge 310 ]; then
                PYTHON_BOOTSTRAP="$candidate"; break
            fi
        fi
    done
    if [ -z "$PYTHON_BOOTSTRAP" ]; then
        echo "  ✗ ERROR: no Python 3.10+ found via Homebrew. Run: brew install python@3.12"
        exit 1
    fi

    rm -rf "$VENV_DIR"
    "$PYTHON_BOOTSTRAP" -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --quiet --upgrade pip
    "$VENV_DIR/bin/pip" install --quiet \
        'requests>=2.31.0,<3.0' \
        'keyring>=24.0.0,<26.0' \
        'pandas>=2.1.0,<3.0' \
        'openpyxl>=3.1.0,<4.0'
    rm -rf "$VENV_DIR"/lib/python*/site-packages/pyarrow* 2>/dev/null || true
    echo "  ✓ venv ready (using $PYTHON_BOOTSTRAP)"
else
    echo "  ✓ venv already at $VENV_DIR"
fi

# 4. Build a plist that points to the installed wrapper (not the source)
#    Use sed to rewrite the path in a temp file, then install.
TMP_PLIST="$(mktemp)"
sed "s|$SCHEDULER_DIR/job_a.sh|$JOB_A_INSTALLED|g" "$SCHEDULER_DIR/com.durabrake.backlog.plist" > "$TMP_PLIST"

mkdir -p "$HOME/Library/LaunchAgents"
cp "$TMP_PLIST" "$PLIST_DST"
rm "$TMP_PLIST"
echo "  ✓ plist installed to $PLIST_DST (points to App Support wrapper)"

# 5. Reload the launchd job (bootout removes prior instance; failures OK)
GUI_TARGET="gui/$(id -u)"
launchctl bootout "$GUI_TARGET/$PLIST_LABEL" 2>/dev/null || true
launchctl bootstrap "$GUI_TARGET" "$PLIST_DST"
echo "  ✓ launchd job loaded as $PLIST_LABEL"

# 6. Verify
echo ""
echo "▶ Verification:"
echo ""
launchctl print "$GUI_TARGET/$PLIST_LABEL" 2>&1 | grep -E '^\s*(state|path|run interval)' || true

echo ""
echo "──────────────────────────────────────────────────────────────────────"
echo "  ONE MORE STEP — run this with sudo to wake the Mac at 23:43 nightly"
echo "──────────────────────────────────────────────────────────────────────"
echo ""
echo "  sudo pmset repeat wake MTWRFSU 23:43"
echo ""
echo "  Why: launchd's 23:45 trigger only fires when the Mac is awake. This"
echo "  pmset schedule wakes the Mac briefly each night at 23:43 so the job"
echo "  has 2 minutes of guaranteed awake-time to start. Almost-zero battery"
echo "  impact (a few seconds of wake/sleep cycle on a plugged-in Mac)."
echo ""
echo "  Verify after running: pmset -g sched"
echo ""
echo "  To uninstall everything: scheduler/uninstall.sh"
