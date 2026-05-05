#!/bin/zsh
# Job A wrapper: end-of-month backlog snapshot (Mac launchd entry point).
#
# IMPORTANT: This file is the source-of-truth, but its installed copy lives at
#   ~/Library/Application Support/DuraBrakeDashboard/job_a.sh
# This is intentional. macOS TCC sandboxes launchd jobs and blocks them
# from reading scripts inside ~/Library/CloudStorage/* without explicit
# privacy grants. ~/Library/Application Support/ is in launchd's default
# read scope, so the installed copy runs without any TCC prompts.
#
# Invoked by launchd at 23:45 daily. The Python script's date gate
# ensures it only fires on the last calendar day of the month —
# every other night is a sub-second no-op skip.
#
# Logs land in:
#   logs/backlog_snapshot_{YY.MM}.log    — Python's structured log
#   logs/launchd_stdout.log              — captured stdout (plist redirect)
#   logs/launchd_stderr.log              — captured stderr (plist redirect)

set -euo pipefail

PROJECT_ROOT="/Users/sculls/Library/CloudStorage/Box-Box/DuraParts/Finance/KPI Dashboard"
VENV_DIR="$HOME/.durabrake-venv"
VENV_PYTHON="$VENV_DIR/bin/python3"

# Python 3.10+ required (codebase uses str | None union syntax).
# /usr/bin/python3 on macOS is 3.9 — too old. Prefer Homebrew.
PYTHON_BOOTSTRAP=""
for candidate in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
    if [ -x "$candidate" ]; then
        version="$("$candidate" -c 'import sys; print(f"{sys.version_info.major}{sys.version_info.minor}")' 2>/dev/null || echo 0)"
        if [ "$version" -ge 310 ]; then
            PYTHON_BOOTSTRAP="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON_BOOTSTRAP" ]; then
    echo "[job_a] ERROR: no Python 3.10+ found. Install via 'brew install python@3.12' or similar." >&2
    exit 1
fi

# Idempotent venv bootstrap. ~/.durabrake-venv is persistent (unlike /tmp).
# Rebuilds only if missing or python is broken.
if [ ! -x "$VENV_PYTHON" ] || ! "$VENV_PYTHON" -c 'import keyring, requests, pandas, openpyxl' 2>/dev/null; then
    echo "[job_a] bootstrapping venv at $VENV_DIR with $PYTHON_BOOTSTRAP"
    rm -rf "$VENV_DIR"
    "$PYTHON_BOOTSTRAP" -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --quiet --upgrade pip
    "$VENV_DIR/bin/pip" install --quiet \
        'requests>=2.31.0,<3.0' \
        'keyring>=24.0.0,<26.0' \
        'pandas>=2.1.0,<3.0' \
        'openpyxl>=3.1.0,<4.0'
    # Defensive: pip on Python 3.14 sometimes installs a broken pyarrow stub
    # that pandas import-checks. Knock it out if present.
    rm -rf "$VENV_DIR"/lib/python*/site-packages/pyarrow* 2>/dev/null || true
fi

cd "$PROJECT_ROOT"
exec "$VENV_PYTHON" scripts/capture_backlog_snapshot.py "$@"
