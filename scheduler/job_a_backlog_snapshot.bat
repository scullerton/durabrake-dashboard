@echo off
REM ============================================================================
REM Job A - DuraBrake Backlog Snapshot
REM Schedule: Daily at 11:45 PM
REM Python handles the "last day of month" gate internally.
REM ============================================================================

cd /d "C:\Users\scull\Box\DuraParts\Finance\KPI Dashboard"
python scripts\capture_backlog_snapshot.py
exit /b %ERRORLEVEL%
