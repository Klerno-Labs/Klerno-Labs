#!/usr/bin/env powershell
<#
.SYNOPSIS
Klerno Labs Enterprise Edition - Startup Script

.DESCRIPTION
Starts the enterprise-grade Klerno Labs application with all TOP 0.1% features enabled.

.PARAMETER Mode
The startup mode: 'enterprise' (default) or 'simple'

.PARAMETER Port
The port to run on (default: 8002 for enterprise, 8001 for simple)

.EXAMPLE
.\start_enterprise.ps1
.\start_enterprise.ps1 -Mode simple -Port 8080
#>

param(
    [Parameter()]
    [ValidateSet("enterprise", "simple")]
    [string]$Mode = "enterprise",

    [Parameter()]
    [int]$Port = 0
)

# Set default ports
if ($Port -eq 0) {
    if ($Mode -eq "enterprise") {
        $Port = 8002
    }
    else {
        $Port = 8001
    }
}

# Clear screen
Clear-Host

# Banner
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "🚀 KLERNO LABS ENTERPRISE EDITION" -ForegroundColor Yellow
Write-Host "   TOP 0.1% Advanced Transaction Analysis Platform" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Environment check
if (!(Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "❌ Virtual environment not found. Please run from main project directory." -ForegroundColor Red
    Write-Host "   Expected: .venv\Scripts\python.exe" -ForegroundColor Yellow
    exit 1
}

# Display configuration
Write-Host "💼 Mode: $($Mode.ToUpper())" -ForegroundColor Cyan
Write-Host "🌐 Port: $Port" -ForegroundColor Cyan
Write-Host "📁 Directory: $(Get-Location)" -ForegroundColor Cyan
Write-Host ""

# Set environment variables for enterprise mode
if ($Mode -eq "enterprise") {
    $env:ENTERPRISE_MODE = "true"
    $env:ENVIRONMENT = "production"
    Write-Host "🏢 Enterprise features: ENABLED" -ForegroundColor Green
    Write-Host "   ✓ Advanced Security" -ForegroundColor Green
    Write-Host "   ✓ Enterprise Monitoring" -ForegroundColor Green
    Write-Host "   ✓ Business Analytics" -ForegroundColor Green
    Write-Host "   ✓ ISO20022 Compliance" -ForegroundColor Green
    Write-Host "   ✓ AI Processing" -ForegroundColor Green
    Write-Host "   ✓ Guardian Protection" -ForegroundColor Green
    Write-Host "   ✓ XRPL Integration" -ForegroundColor Green
    Write-Host "   ✓ Performance Optimization" -ForegroundColor Green
}
else {
    $env:ENTERPRISE_MODE = "false"
    $env:ENVIRONMENT = "development"
    Write-Host "🏠 Simple mode: Basic features only" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🔧 Starting application..." -ForegroundColor Cyan

try {
    if ($Mode -eq "enterprise") {
        # Start enterprise application
        & "..\..\.venv\Scripts\python.exe" "enterprise_main_v2.py" --host "127.0.0.1" --port $Port
    }
    else {
        # Start simple application
        & "..\..\.venv\Scripts\python.exe" "start_clean.py" --port $Port
    }
}
catch {
    Write-Host ""
    Write-Host "❌ Failed to start application: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Ensure you're in the CLEAN_APP directory" -ForegroundColor White
    Write-Host "2. Check that the virtual environment is activated" -ForegroundColor White
    Write-Host "3. Install dependencies: pip install -r requirements-enterprise.txt" -ForegroundColor White
    Write-Host "4. Check that port $Port is available" -ForegroundColor White
    exit 1
}
