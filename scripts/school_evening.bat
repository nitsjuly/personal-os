@echo off
REM school_evening.bat — Send evening nudge (only if urgent items exist)
REM Runs at 8:00 PM via Task Scheduler

cd /d "C:\path\to\personal-os"
call venv\Scripts\activate.bat
python run_school.py --mode=evening >> logs\school_evening.log 2>&1
