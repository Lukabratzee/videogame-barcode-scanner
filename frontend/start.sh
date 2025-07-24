#!/bin/bash

# Remove stale X11 lock file
rm -f /tmp/.X99-lock

# Start Xvfb in background with complete isolation
echo "Starting Xvfb virtual display on :99..."
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset -nolisten tcp &

# Wait for Xvfb to start and verify
sleep 3
if pgrep -f "Xvfb :99" > /dev/null; then
    echo "✅ Xvfb started successfully on display :99"
else
    echo "❌ Failed to start Xvfb"
    exit 1
fi

# Completely isolate X11 from host
export DISPLAY=:99
export XAUTHORITY=/tmp/.docker.xauth
export CHROME_BIN=/usr/bin/chromium
export CHROMEDRIVER_BIN=/usr/local/bin/chromedriver

# Set Streamlit config to skip welcome screen
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Test browser setup to ensure isolation
echo "Testing browser setup..."
chromium --version
chromedriver --version

# Start Streamlit
echo "Starting Streamlit application..."
exec streamlit run /app/frontend.py --server.port=8501 --server.address=0.0.0.0 --browser.gatherUsageStats=false --global.developmentMode=false 