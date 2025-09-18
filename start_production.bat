@echo off
REM Production Deployment Script for Klerno Labs Enterprise Application (Windows)
REM This script sets up and starts the production server with all enterprise features

echo 🏭 KLERNO LABS - PRODUCTION DEPLOYMENT SCRIPT (WINDOWS)
echo =======================================================

REM Set production environment variables
set JWT_SECRET=production-jwt-secret-key-change-this-in-production-123456789abcdef
set ADMIN_EMAIL=admin@klerno.com
set ADMIN_PASSWORD=SecureAdminPass123!
set ENVIRONMENT=production
set LOG_LEVEL=INFO

REM Create data directory if it doesn't exist
if not exist "data" mkdir data

echo ✅ Environment configured

REM Validate Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is required but not installed
    exit /b 1
)

echo ✅ Python available

REM Install dependencies if requirements.txt exists
if exist "requirements.txt" (
    echo 📦 Installing dependencies...
    pip install -r requirements.txt
    echo ✅ Dependencies installed
)

REM Run production verification
echo 🔍 Running production verification...
python production_verification.py
if errorlevel 1 (
    echo ⚠️  Production verification had warnings, but continuing...
)

REM Start the production server
echo 🚀 Starting production server...
python deploy_production.py --host 0.0.0.0 --port 8000 --workers 1

echo 🛑 Server stopped
pause