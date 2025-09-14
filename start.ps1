# Klerno Labs Launcher - Simple Version
param(
    [int]$Port = 10000
)

$ErrorActionPreference = "Stop"

# Simple launcher that delegates to run-311.ps1
Write-Host "===== Klerno Labs Launcher =====" -ForegroundColor Cyan
Write-Host "Delegating to run-311.ps1 (Python 3.11)" -ForegroundColor DarkCyan

$runner = Join-Path $PSScriptRoot "run-311.ps1"
if (!(Test-Path $runner)) {
    Write-Error "run-311.ps1 not found next to start.ps1. Please keep both scripts in the repo root."
    exit 1
}

# Run the Python 3.11 script with the provided port
& $runner -Port $Port