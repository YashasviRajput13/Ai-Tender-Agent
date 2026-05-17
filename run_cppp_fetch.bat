@echo off
title Tender AI - CPPP Bulk Fetch
chcp 65001 >nul
echo.
echo ============================================================
echo   CPPP Bulk Tender Fetcher
echo   Scraping live tenders from eprocure.gov.in
echo ============================================================
echo.

cd /d "%~dp0"

set KEYWORD=%~1
set PAGES=%~2

if "%KEYWORD%"=="" set KEYWORD=
if "%PAGES%"=="" set PAGES=2

echo Keyword filter : %KEYWORD%
echo Pages to scrape: %PAGES%
echo.

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
uv run python cppp_bulk_fetch.py %KEYWORD% %PAGES%

echo.
echo ============================================================
echo   Done! Run run_dashboard.bat to view results.
echo ============================================================
pause
