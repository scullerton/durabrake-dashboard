# Scheduler — Mac launchd setup

End-of-month backlog snapshot, automated on macOS.

## What this does

At 23:45 every night, your Mac runs `scripts/capture_backlog_snapshot.py`. The script's date-gate makes it a sub-second no-op on most nights and a real FileMaker pull only on the last calendar day of the month. The captured backlog lands in `inputs/{YY.MM}/Backlog_YYYY-MM-DD.xlsx` (Box-synced).

## Files in this folder

| File | Purpose |
|---|---|
| `job_a.sh` | Shell wrapper invoked by launchd. Bootstraps a Python venv (~/.durabrake-venv) on first run, then executes the snapshot script. |
| `com.durabrake.backlog.plist` | launchd configuration. Source-of-truth lives here; `install.sh` copies it into `~/Library/LaunchAgents/`. |
| `install.sh` | One-time installer. Idempotent — safe to re-run after edits. |
| `uninstall.sh` | Clean removal. |
| `job_a_backlog_snapshot.bat`, `job_b_monthly_dashboard.bat` | Legacy Windows Task Scheduler wrappers. Kept for git history; not used on Mac. |

## Install

```bash
cd "/Users/sculls/Library/CloudStorage/Box-Box/DuraParts/Finance/KPI Dashboard"
./scheduler/install.sh
```

The installer prints **one** sudo command at the end — it can't be auto-run because `pmset` requires elevated privileges. Copy/paste it once:

```bash
sudo pmset repeat wake MTWRFSU 23:43
```

## How it stays reliable

| Layer | What it ensures |
|---|---|
| **launchd `StartCalendarInterval`** | Fires at 23:45 every night the Mac is awake |
| **`pmset repeat wake`** | Wakes the Mac from sleep at 23:43 nightly so launchd has an awake host to fire on |
| **Python date-gate inside the script** | Only does real work on the last day of the month; other nights it's a no-op |
| **`fmp_client.py` exit codes** | Network/timeout failures exit 2; launchd will fire again at next trigger (next night). For the EoM trigger that's after-the-fact, but the manual fallback below covers it. |

## Verify install

```bash
# Is the launchd job registered?
launchctl list | grep durabrake

# What's its full state?
launchctl print "gui/$(id -u)/com.durabrake.backlog-snapshot"

# Is the pmset wake scheduled?
pmset -g sched
# Should show:  repeat wake MTWRFSU 23:43:00
```

## Manual test (no waiting until 23:45)

Trigger the job right now to confirm it works end-to-end:

```bash
launchctl kickstart "gui/$(id -u)/com.durabrake.backlog-snapshot"
```

Today's run will hit the date-gate and exit cleanly (assuming today isn't the last day of the month). Check the log:

```bash
tail logs/backlog_snapshot_$(date +%y.%m).log
# Expected: "Today is day N; last day of month is M. Skipping."
```

For a real end-to-end test that actually pulls from FileMaker:

```bash
~/.durabrake-venv/bin/python scripts/capture_backlog_snapshot.py --force --period 26.05
```

The `--force` bypasses the date-gate so you don't have to wait until month-end. The new file lands in `inputs/26.05/`.

## Manual recovery (if the scheduled run was missed)

If the Mac was off / on battery / unplugged at 23:45 on the last day of the month, the snapshot is missed. To recover (next morning):

```bash
~/.durabrake-venv/bin/python scripts/capture_backlog_snapshot.py --force --period 26.05
```

The captured snapshot will reflect *now*, not 23:45 last night — orders shipped overnight are gone, orders booked overnight are in. Document the discrepancy if the variance matters for the monthly report.

## Failure modes and what they look like

| Symptom | Likely cause | Fix |
|---|---|---|
| Log says "Backlog file(s) already present (<6h old): [...] Skipping (idempotent)" | Real fresh snapshot already captured (good) | Nothing — this is the success path on a re-trigger |
| Log says "Found N stale file(s) — treating as leftover" | Old test data or unrelated file in the inputs folder | Auto-archived to `.stale/`; new fetch proceeds |
| `launchctl list` shows exit code != 0 | Bootstrap failure (venv, network, FM auth) | Check `logs/launchd_stderr.log` and `logs/backlog_snapshot_{YY.MM}.log` |
| FM error code 105 | Layout permissions issue | `web` user lost access — re-run setup with the `readonly` user (or whoever the FM admin assigned) |
| FM error code 401 / "invalid credentials" | Password rotated in FM, not yet updated in keychain | `python scripts/fmp_client.py --setup` and update the password |
| pmset shows no wake schedule | `sudo pmset repeat wake MTWRFSU 23:43` not run | Re-run the sudo command from install.sh output |

## Uninstall

```bash
./scheduler/uninstall.sh
sudo pmset repeat cancel    # if you also want to stop the nightly wake
```

Leaves `~/.durabrake-venv/` and `logs/` in place (harmless if left; remove manually if desired).

## Assumptions baked into this setup

1. **Mac is plugged into power overnight on the last day of each month.** If on battery with lid closed, the wake-from-sleep may fail and the trigger is missed. Manual recovery covers this.
2. **You stay logged in** (the Mac can sleep, but don't log out). Logging out locks the user keychain, blocking `keyring` from reading the FM credentials. Default Mac behavior with lid-close is "sleep but stay logged in" — that works fine.
3. **The Mac has Internet at 23:45.** Required for FM Cloud connectivity. Almost always true on a home network.

If any of these become wrong (extended travel, etc.), use the manual fallback the next morning.
