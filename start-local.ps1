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

# Pick a suitable Python interpreter from common local virtualenvs or PATH
$candidates = @(
    ".\\.venv-1\\Scripts\\python.exe",
    ".\\.venv-py311\\Scripts\\python.exe",
    ".\\.venv-3.11\\Scripts\\python.exe",
    ".\\.venv\\Scripts\\python.exe"
)

$python = $null
foreach ($p in $candidates) {
    if (Test-Path -Path $p) { $python = $p; break }
}

if (-not $python) {
    # Try python from PATH, then Windows launcher
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $python = "python"
    }
    elseif (Get-Command py -ErrorAction SilentlyContinue) {
        $python = "py -3.11"
    }
}

if (-not $python) {
    Write-Host "No local Python interpreter found. Create a venv and try again:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv-3.11; .\\.venv-3.11\\Scripts\\Activate.ps1; python -m pip install -U pip; pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

Write-Host "Using Python interpreter: $python"
Write-Host "Starting uvicorn app.main:app (use Ctrl+C to stop)..."
& $python -m uvicorn app.main:app --reload
