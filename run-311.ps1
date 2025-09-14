# Klerno Labs local runner for Python 3.11
param(
    [int]$Port = 10000,
    [switch]$NoBrowser,
    [switch]$Debug,
    [string]$LogLevel = "info",
    [switch]$SkipEnvCheck
)
$ErrorActionPreference = "Stop"

# Ensure .venv311 exists with Python 3.11
if (-not (Test-Path ".venv311/Scripts/python.exe")) {
    Write-Host "Python 3.11 virtual environment not found, creating one..." -ForegroundColor Yellow
    $pyLauncher = Join-Path $env:SystemRoot "py.exe"
    if (Test-Path $pyLauncher) {
        & $pyLauncher "-3.11" "-m" "venv" ".venv311"
    } else {
        try { & py "-3.11" "-m" "venv" ".venv311" } catch {}
        if (-not (Test-Path ".venv311/Scripts/python.exe")) {
            $verOut = & python --version 2>$null
            if ($verOut -match "Python 3\.11") {
                & python -m venv .venv311
            } else {
                Write-Error "Python 3.11 not found. Install Python 3.11 from https://www.python.org/downloads/"
                exit 1
            }
        }
    }
    Write-Host "Virtual environment created successfully." -ForegroundColor Green
}

# Activate venv
Write-Host "Activating Python 3.11 virtual environment..." -ForegroundColor Blue
. .\.venv311\Scripts\Activate.ps1

# Install requirements if needed
try {
    python -c "import uvicorn" 2>$null
    Write-Host "Dependencies already installed." -ForegroundColor Green
} catch {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    python -m pip install --upgrade pip setuptools wheel
    
    # Use consolidated requirements file if it exists, otherwise fall back to requirements.txt
    if (Test-Path "requirements-consolidated.txt") {
        Write-Host "Using consolidated requirements file..." -ForegroundColor Cyan
        python -m pip install -r requirements-consolidated.txt
    } else {
        Write-Host "Using standard requirements file..." -ForegroundColor Yellow
        python -m pip install -r requirements.txt
    }
    Write-Host "Dependencies installed successfully." -ForegroundColor Green
}

# Check if .env exists, if not create a sample one
if (-not (Test-Path ".env")) {
    Write-Host "Creating sample .env file..." -ForegroundColor Yellow
    @"
# ===== Klerno Labs Environment Configuration =====
# Created: $(Get-Date -Format "yyyy-MM-dd")
# Environment: Development

# ===== App Configuration =====
APP_ENV=dev
DEBUG=true
SECRET_KEY=klerno_labs_secret_key_2025_very_secure_32_chars_minimum
PORT=10000
HOST=0.0.0.0
LOG_LEVEL=info

# ===== Database Configuration =====
# Switch between sqlite (dev) and postgres (prod)
DATABASE_URL=sqlite:///./data/klerno.db
# DATABASE_URL=postgresql://user:password@localhost:5432/klerno

# ===== XRPL Settings =====
XRPL_NET=testnet
DESTINATION_WALLET=rPT1Sjq2YGrBMTttX4GZHjKu9dyfzbpAYe
SUB_PRICE_XRP=10
SUB_DURATION_DAYS=30

# ===== Security =====
# JWT settings
JWT_SECRET=your_jwt_secret_here_should_be_at_least_32_chars
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# ===== Email Configuration =====
SENDGRID_API_KEY=your_sendgrid_key_here
EMAIL_FROM=noreply@klernolabs.com
EMAIL_NAME=Klerno Labs

# ===== Feature Flags =====
ENABLE_XRPL_PAYMENTS=true
DEMO_MODE=true
ENABLE_ANALYTICS=false
ENABLE_RATE_LIMITING=true

# ===== Deployment =====
# Set to 'render' when deploying to Render.com
DEPLOYMENT_PLATFORM=local
"@ | Out-File -FilePath ".env" -Encoding utf8
    Write-Host "Sample .env file created." -ForegroundColor Green
}

# Determine log level
if ($Debug) {
    $LogLevel = "debug"
}

# Run environment check unless skipped
if (-not $SkipEnvCheck) {
    $envCheckerPath = Join-Path $PSScriptRoot "scripts\check_environment.ps1"
    if (Test-Path $envCheckerPath) {
        Write-Host "Running environment check..." -ForegroundColor Blue
        $envCheckResult = & $envCheckerPath
        if (-not $envCheckResult) {
            Write-Host "Environment check found issues. Do you want to continue anyway? (y/n)" -ForegroundColor Yellow -NoNewline
            $continue = Read-Host " "
            if ($continue -ne "y") {
                Write-Host "Exiting due to environment check failures." -ForegroundColor Red
                exit 1
            }
            Write-Host "Continuing despite environment check warnings/errors..." -ForegroundColor Yellow
        }
    } else {
        Write-Host "Environment checker not found at $envCheckerPath" -ForegroundColor Yellow
    }
}

# Start server
Write-Host "Starting server on http://localhost:$Port" -ForegroundColor Green
Write-Host "API documentation available at http://localhost:$Port/docs" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor DarkGray

# Open browser automatically unless -NoBrowser switch is used
if (-not $NoBrowser) {
    try {
        Start-Process "http://localhost:$Port"
    } catch {
        Write-Host "Could not open browser automatically." -ForegroundColor Yellow
    }
}

# Run the application
uvicorn app.main:app --host 0.0.0.0 --port $Port --log-level $LogLevel