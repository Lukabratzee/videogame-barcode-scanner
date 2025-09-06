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

# Initialize database and run migrations (idempotent)
echo "🔍 Initializing database and running migrations..."
python3 database_setup.py || true
python3 migrate_gallery_v1.py || true
python3 add_price_history.py || true
python3 migrate_artwork_columns.py || true
python3 add_region_column.py || true
python3 add_date_added_column.py || true

# Ensure ChromeDriver matches Chromium version (runtime safety)
echo "🔧 Verifying ChromeDriver version matches Chromium..."
if command -v chromium &> /dev/null; then
  CHROME_MAJOR=$(chromium --version | awk '{print $2}' | cut -d'.' -f1)
  if command -v chromedriver &> /dev/null; then
    DRIVER_MAJOR=$(chromedriver --version | awk '{print $2}' | cut -d'.' -f1)
  else
    DRIVER_MAJOR=""
  fi
  if [ "$CHROME_MAJOR" != "$DRIVER_MAJOR" ]; then
    echo "Updating ChromeDriver to match Chromium major ${CHROME_MAJOR}..."
    CFT_VERSION=$(curl -sSL "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_${CHROME_MAJOR}")
    if [ -n "$CFT_VERSION" ]; then
      wget -q -O /tmp/chromedriver-linux64.zip "https://storage.googleapis.com/chrome-for-testing-public/${CFT_VERSION}/linux64/chromedriver-linux64.zip" && \
      unzip -o /tmp/chromedriver-linux64.zip -d /tmp >/dev/null && \
      mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
      chmod +x /usr/local/bin/chromedriver && \
      rm -rf /tmp/chromedriver-linux64.zip /tmp/chromedriver-linux64
      echo "✅ ChromeDriver updated to ${CFT_VERSION}"
    else
      echo "⚠️ Could not resolve Chrome for Testing version for major ${CHROME_MAJOR}"
    fi
  else
    echo "✅ ChromeDriver major matches Chromium (${CHROME_MAJOR})"
  fi
fi
python3 add_date_added_column.py || true

# Start the Flask application
echo "Starting Flask application..."
exec python3 app.py
