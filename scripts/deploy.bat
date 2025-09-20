@echo off
REM Klerno Labs Deployment Script for Windows

set ENVIRONMENT=%1
if "%ENVIRONMENT%"=="" set ENVIRONMENT=staging

echo Deploying to %ENVIRONMENT% environment...

REM Build Docker image
echo Building Docker image...
docker build -t klerno-labs:latest .

REM Deploy with docker-compose
echo Starting services...
docker-compose up -d

echo Deployment completed successfully!
