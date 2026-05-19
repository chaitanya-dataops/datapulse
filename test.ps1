# DataPulse Test Runner
# Run all tests before deployment

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DataPulse Pre-Deployment Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment
if (Test-Path ".\venv\Scripts\Activate.ps1") {
    .\venv\Scripts\Activate.ps1
}

# Install pytest if needed
pip install pytest -q 2>$null

# Run the pre-deployment checks
Write-Host "Running pre-deployment checks..." -ForegroundColor Yellow
python tests/run_pre_deploy_checks.py

$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host ""
    Write-Host "All tests passed! Ready to deploy." -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "Tests failed. Please fix issues before deploying." -ForegroundColor Red
    Write-Host ""
}

exit $exitCode
