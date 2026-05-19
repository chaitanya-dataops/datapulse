@echo off
REM Quick start script for DataPulse

REM Check if venv exists
if exist "venv\Scripts\activate.bat" (
    echo [OK] Virtual environment found
    call venv\Scripts\activate.bat
) else (
    echo [SETUP] Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [SETUP] Installing dependencies...
    pip install -r requirements-lock.txt
)

echo.
echo Starting DataPulse...
echo.
streamlit run app.py
