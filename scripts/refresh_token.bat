@echo off
REM refresh_token.bat — Refresh Savvas bearer token via Playwright
REM Runs at 6:30 AM via Task Scheduler

cd /d "C:\path\to\personal-os"
call venv\Scripts\activate.bat
python savvas_refresh_token.py >> logs\refresh.log 2>&1
