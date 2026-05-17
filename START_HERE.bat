@echo off
chcp 65001 >nul
title Tender AI - Main Launcher
color 0A

cls
echo.
echo  ========================================================
echo   AI TENDER INTELLIGENCE SYSTEM
echo   Powered by CrewAI + CPPP + OpenRouter
echo  ========================================================
echo.
echo   [1]  Launch Dashboard     (Streamlit UI)
echo   [2]  Fetch Now from CPPP  (Quick bulk fetch)
echo   [3]  Start Auto-Scheduler (Fetch every 6 hours)
echo   [4]  Run CrewAI Pipeline  (Full AI agent workflow)
echo   [5]  Install/Update deps  (uv sync)
echo   [0]  Exit
echo.
echo  ========================================================
echo.

set /p CHOICE="  Enter your choice (0-5): "

cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

if "%CHOICE%"=="1" goto DASHBOARD
if "%CHOICE%"=="2" goto FETCH
if "%CHOICE%"=="3" goto SCHEDULER
if "%CHOICE%"=="4" goto PIPELINE
if "%CHOICE%"=="5" goto INSTALL
if "%CHOICE%"=="0" goto EXIT

echo.
echo   Invalid choice. Please try again.
pause
goto :EOF

:DASHBOARD
echo.
echo   Launching Dashboard at http://localhost:8501 ...
echo.
start "Tender Dashboard" cmd /k "chcp 65001 && cd /d %~dp0 && set PYTHONUTF8=1 && uv run streamlit run dashboard.py"
goto EXIT

:FETCH
echo.
set /p KEYWORD="  Keyword to search (leave blank for all): "
set /p PAGES="  Number of pages to scrape [default 2]: "
if "%PAGES%"=="" set PAGES=2
echo.
echo   Fetching from CPPP...
echo.
uv run python cppp_bulk_fetch.py %KEYWORD% %PAGES%
echo.
pause
goto EXIT

:SCHEDULER
echo.
echo   Starting Auto-Scheduler (every 6 hours)...
echo   Press Ctrl+C in the new window to stop.
echo.
start "Tender Scheduler" cmd /k "chcp 65001 && cd /d %~dp0 && set PYTHONUTF8=1 && uv run python scheduler.py"
goto EXIT

:PIPELINE
echo.
set /p QUERY="  Enter search query [default: Road Construction]: "
if "%QUERY%"=="" set QUERY=Road Construction
echo.
echo   Starting CrewAI Pipeline for: %QUERY%
echo.
uv run python main.py %QUERY%
pause
goto EXIT

:INSTALL
echo.
echo   Installing / syncing dependencies...
echo.
uv sync
uv add schedule langchain-openai sqlalchemy chromadb sentence-transformers
echo.
echo   Done!
pause
goto EXIT

:EXIT
