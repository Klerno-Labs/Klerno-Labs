# Klerno Labs - Clean Startup Script
# This script sets the required environment variables and starts the server

Write-Host "[STARTUP] Klerno Labs Enterprise Application" -ForegroundColor Green
Write-Host "[STARTUP] Setting environment variables..." -ForegroundColor Yellow

# Set required JWT secret
$env:JWT_SECRET = "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456"

Write-Host "[STARTUP] Environment variables set" -ForegroundColor Green
Write-Host "[STARTUP] Starting Uvicorn server..." -ForegroundColor Yellow
Write-Host "" 

# Change to application directory
Set-Location $PSScriptRoot

# Start the application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

Write-Host "" 
Write-Host "[SHUTDOWN] Server stopped" -ForegroundColor Red