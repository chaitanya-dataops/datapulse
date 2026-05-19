# Quick start script for DataPulse (PowerShell)

# Check if venv exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "[OK] Virtual environment found" -ForegroundColor Green
    .\venv\Scripts\Activate.ps1
} else {
    Write-Host "[SETUP] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    Write-Host "[SETUP] Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements-lock.txt
}

Write-Host ""
Write-Host "Starting DataPulse..." -ForegroundColor Cyan
Write-Host ""
streamlit run app.py
