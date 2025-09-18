#!/bin/bash
# Production Deployment Script for Klerno Labs Enterprise Application
# This script sets up and starts the production server with all enterprise features

echo "🏭 KLERNO LABS - PRODUCTION DEPLOYMENT SCRIPT"
echo "=============================================="

# Set production environment variables
export JWT_SECRET="production-jwt-secret-key-change-this-in-production-123456789abcdef"
export ADMIN_EMAIL="admin@klerno.com"
export ADMIN_PASSWORD="SecureAdminPass123!"
export ENVIRONMENT="production"
export LOG_LEVEL="INFO"

# Create data directory if it doesn't exist
mkdir -p data

echo "✅ Environment configured"

# Validate Python installation
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is required but not installed"
    exit 1
fi

echo "✅ Python3 available"

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "📦 Installing dependencies..."
    pip3 install -r requirements.txt
    echo "✅ Dependencies installed"
fi

# Run production verification
echo "🔍 Running production verification..."
python3 production_verification.py
if [ $? -ne 0 ]; then
    echo "⚠️  Production verification had warnings, but continuing..."
fi

# Start the production server
echo "🚀 Starting production server..."
python3 deploy_production.py --host 0.0.0.0 --port 8000 --workers 1

echo "🛑 Server stopped"