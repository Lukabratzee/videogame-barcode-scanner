# Use Python 3.11 slim as base image for better ARM64 support
FROM python:3.11-slim

# We need root privileges to install packages
USER root

# Create /app as our working directory
WORKDIR /app

# Set environment variables (NO Chrome environment needed)
ENV DEBIAN_FRONTEND=noninteractive
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Install system dependencies (NO Chrome - all scraping happens via backend API)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

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

# Create ~/.streamlit folder and copy config
RUN mkdir -p /root/.streamlit
RUN if [ -d "/app/.streamlit" ]; then cp -r /app/.streamlit/* /root/.streamlit/; fi

# Create symlinks for browser compatibility
RUN ln -sf /usr/bin/chromium /usr/bin/google-chrome-stable && \
    ln -sf /usr/bin/chromedriver /usr/local/bin/chromedriver

# Create a simple Streamlit config to skip first-time setup
RUN echo '[browser]' > /root/.streamlit/config.toml && \
    echo 'gatherUsageStats = false' >> /root/.streamlit/config.toml && \
    echo '[global]' >> /root/.streamlit/config.toml && \
    echo 'developmentMode = false' >> /root/.streamlit/config.toml

# Make the start script executable
RUN chmod +x /app/start.sh

# Expose Streamlit port
EXPOSE 8501

# Use the start script
CMD ["/app/start.sh"]