@echo off
REM school_morning.bat — Send morning school digest
REM Runs at 7:00 AM via Task Scheduler

cd /d "C:\path\to\personal-os"
call venv\Scripts\activate.bat
python run_school.py --mode=morning >> logs\school_morning.log 2>&1
