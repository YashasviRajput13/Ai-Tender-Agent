@echo off
title Tender AI - Auto Scheduler (Running)
chcp 65001 >nul
echo.
echo ============================================================
echo   Tender Intelligence Auto-Scheduler
echo   Fetches new tenders from CPPP every 6 hours
echo   Press Ctrl+C to stop
echo ============================================================
echo.

cd /d "%~dp0"

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

uv run python scheduler.py

pause
