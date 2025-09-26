<#
start-local.ps1
Sets sensible development environment variables for this project (session-only) and starts uvicorn.
Usage: Run from repository root in PowerShell: .\start-local.ps1
#>

Write-Host "Setting session environment variables for local development..."
$env:APP_ENV = "development"
$env:X_API_KEY = "dev-local-api-key"
$env:API_KEY = "dev-local-api-key"
$env:JWT_SECRET = "dev-secret-change-me"
$env:DATABASE_URL = "sqlite:///./data/klerno.db"

Write-Host "Ensuring data directory exists..."
New-Item -Path .\data -ItemType Directory -Force | Out-Null

if (-Not (Test-Path -Path ".\.venv-py311\Scripts\python.exe")) {
    Write-Host "Virtualenv .venv-py311 not found. Create it with: python -m venv .venv-py311" -ForegroundColor Yellow
}

Write-Host "Starting uvicorn app.main:app (use Ctrl+C to stop)..."
& .\.venv-py311\Scripts\python.exe -m uvicorn app.main:app --reload
