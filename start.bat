@echo off
REM Quick start script for StorePilot AI (Windows)
REM Run this from project root: D:\storepilot-ai

echo ========================================
echo  StorePilot AI - Quick Start
echo ========================================

REM Check if venv exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating venv...
call venv\Scripts\activate

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Running setup (creates DB, runs migrations, seeds data)...
python setup.py

echo.
echo ========================================
echo  Starting backend server...
echo  Open another terminal for frontend!
echo ========================================
echo.

uvicorn app.main:app --reload