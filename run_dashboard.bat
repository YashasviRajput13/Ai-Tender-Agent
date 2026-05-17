@echo off
title Tender AI - Dashboard
chcp 65001 >nul
echo.
echo ============================================================
echo   Tender Intelligence System - Streamlit Dashboard
echo ============================================================
echo.

cd /d "%~dp0"

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo Launching dashboard at http://localhost:8501
echo.
uv run streamlit run dashboard.py

pause
