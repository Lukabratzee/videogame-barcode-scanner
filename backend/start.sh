#!/bin/bash

# Completely isolate from host X11 system
unset XAUTHORITY
export DISPLAY=:99
export XVFB_WHD="1920x1080x24"

# Remove stale X11 lock file
rm -f /tmp/.X99-lock

# Start Xvfb in the background with specific isolation
echo "Starting Xvfb virtual display on :99..."
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset -nolisten tcp -dpi 96 &
XVFB_PID=$!

# Wait a moment for Xvfb to start
sleep 3

# Verify Xvfb is running
if ps -p $XVFB_PID > /dev/null; then
    echo "✅ Xvfb started successfully on display :99"
else
    echo "❌ Failed to start Xvfb"
    exit 1
fi

# Test browser setup
echo "Testing browser setup..."
if command -v chromium &> /dev/null; then
    chromium --version
else
    echo "Chromium not found"
fi

if command -v chromedriver &> /dev/null; then
    chromedriver --version
else
    echo "Chromedriver not found"
fi

# Initialize database if it doesn't exist
echo "🔍 About to initialize database..."
echo "🔍 Current working directory: $(pwd)"
echo "🔍 Files in current directory:"
ls -la
echo "🔍 Looking for database_setup.py:"
ls -la database_setup.py
echo "🔍 Testing python3 command:"
python3 --version
echo "🔍 Now running database_setup.py..."
python3 database_setup.py
echo "🔍 Database setup completed with exit code: $?"

# Start the Flask application
echo "Starting Flask application..."
exec python3 app.py 