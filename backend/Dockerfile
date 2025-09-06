# Use Python 3.11 slim as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Accept build arguments for configuration
ARG BACKEND_PORT=5001
ARG DATABASE_PATH=games.db

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_BIN=/usr/local/bin/chromedriver
ENV BACKEND_PORT=${BACKEND_PORT}
ENV DATABASE_PATH=${DATABASE_PATH}

# Install system dependencies including Chromium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    chromium \
    # Additional dependencies for Chromium
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

# Install matching ChromeDriver using Chrome for Testing API
# Detect Chromium major version, then fetch corresponding ChromeDriver
RUN CHROME_MAJOR=$(chromium --version | awk '{print $2}' | cut -d'.' -f1) && \
    echo "Detected Chromium major version: ${CHROME_MAJOR}" && \
    CFT_VERSION=$(curl -sSL "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_${CHROME_MAJOR}") && \
    echo "Using Chrome for Testing version: ${CFT_VERSION}" && \
    wget -O /tmp/chromedriver-linux64.zip "https://storage.googleapis.com/chrome-for-testing-public/${CFT_VERSION}/linux64/chromedriver-linux64.zip" && \
    unzip /tmp/chromedriver-linux64.zip -d /tmp && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver-linux64.zip /tmp/chromedriver-linux64

# Create symlinks for compatibility
RUN ln -sf /usr/bin/chromium /usr/bin/google-chrome-stable

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Copy shared modules from parent directory
COPY modules ./modules

# Make the start script executable
RUN chmod +x /app/start.sh

# Expose Flask port (configurable)
EXPOSE ${BACKEND_PORT}

# Use the start script
CMD ["/app/start.sh"]
