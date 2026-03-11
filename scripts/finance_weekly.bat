@echo off
REM finance_weekly.bat — Run weekly finance anomaly check
REM Runs Monday 8:00 AM via Task Scheduler

cd /d "C:\path\to\personal-os"
call venv\Scripts\activate.bat
python agents\finance_agent.py --mode=weekly >> logs\finance.log 2>&1
