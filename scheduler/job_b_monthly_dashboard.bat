@echo off
REM ============================================================================
REM Job B - DuraBrake Monthly Dashboard Generation
REM Schedule: Daily at 6:00 AM
REM Python handles the "day >= 22" gate and idempotent skipping internally.
REM ============================================================================

cd /d "C:\Users\scull\Box\DuraParts\Finance\KPI Dashboard"
python scripts\monthly_automation.py
exit /b %ERRORLEVEL%
