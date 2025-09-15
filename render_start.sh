#!/bin/bash
# This is the script that Render runs to start your service
# It contains fallbacks to ensure something always runs

# Set the port
PORT="${PORT:-8000}"
echo "Using port: $PORT"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found! Trying python..."
    if ! command -v python &> /dev/null; then
        echo "No Python found! Cannot continue."
        exit 1
    fi
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

echo "Using Python command: $PYTHON_CMD"
echo "Python version: $($PYTHON_CMD --version)"

# First try to run the main app
echo "Attempting to start main app..."
if $PYTHON_CMD -m uvicorn app.main:app --host 0.0.0.0 --port $PORT; then
    echo "Main app started successfully!"
    exit 0
fi

# If main app fails, try the healthcheck
echo "Main app failed to start. Falling back to healthcheck..."
if $PYTHON_CMD -m uvicorn healthcheck:app --host 0.0.0.0 --port $PORT; then
    echo "Healthcheck started successfully!"
    exit 0
fi

# If all else fails, run a simple HTTP server
echo "All FastAPI apps failed. Starting simple HTTP server as last resort..."
echo "<html><body><h1>Klerno Labs - Emergency Mode</h1><p>The application is currently experiencing technical difficulties. Please check back later.</p></body></html>" > emergency.html
$PYTHON_CMD -m http.server $PORT

# This should never be reached unless even the HTTP server fails
echo "All server attempts failed!"
exit 1