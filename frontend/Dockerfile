# Use Python 3.11 slim as base image for better ARM64 support
FROM python:3.11-slim

# We need root privileges to install packages
USER root

# Create /app as our working directory
WORKDIR /app

# Accept build arguments for configuration
ARG FRONTEND_PORT=8501
ARG BACKEND_HOST=backend
ARG BACKEND_PORT=5001

# Set environment variables (NO Chrome environment needed)
ENV DEBIAN_FRONTEND=noninteractive
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV FRONTEND_PORT=${FRONTEND_PORT}
ENV BACKEND_HOST=${BACKEND_HOST}
ENV BACKEND_PORT=${BACKEND_PORT}

# Install system dependencies including Chrome and ChromeDriver
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    xvfb \
    procps \
    gnupg \
    unzip \
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

# Install ChromeDriver for the target architecture - use Chrome for Testing API for newer versions
RUN CHROME_VERSION="138.0.7204.168" && \
    echo "Downloading ChromeDriver version: $CHROME_VERSION for linux64" && \
    wget -O /tmp/chromedriver-linux64.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" && \
    unzip /tmp/chromedriver-linux64.zip -d /tmp && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver-linux64.zip /tmp/chromedriver-linux64

# Set Chrome environment variables
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_BIN=/usr/local/bin/chromedriver
ENV DISPLAY=:99

# Create a Python virtual environment in /venv
RUN python3 -m venv /venv --copies

# Make sure venv is first in PATH
ENV PATH="/venv/bin:$PATH"

# Copy requirements and install them
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy local frontend code into /app
COPY . /app

# Copy shared modules from parent directory
COPY ../modules ./modules

# Create ~/.streamlit folder and copy config
RUN mkdir -p /root/.streamlit
RUN if [ -d "/app/.streamlit" ]; then cp -r /app/.streamlit/* /root/.streamlit/; fi

# Create symlinks for browser compatibility
RUN ln -sf /usr/bin/chromium /usr/bin/google-chrome-stable

# Create a simple Streamlit config to skip first-time setup
RUN echo '[browser]' > /root/.streamlit/config.toml && \
    echo 'gatherUsageStats = false' >> /root/.streamlit/config.toml && \
    echo '[global]' >> /root/.streamlit/config.toml && \
    echo 'developmentMode = false' >> /root/.streamlit/config.toml

# Make the start script executable
RUN chmod +x /app/start.sh

# Expose Streamlit port (configurable)
EXPOSE ${FRONTEND_PORT}

# Use the start script
CMD ["/app/start.sh"]