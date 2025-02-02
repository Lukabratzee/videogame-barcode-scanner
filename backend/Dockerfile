# Use a slim Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Fix permissions and remove broken/multiple sources
USER root
RUN mkdir -p /var/lib/apt/lists/partial && chmod -R 777 /var/lib/apt/lists

# Fix GPG key issues & force update repositories
RUN rm -rf /var/lib/apt/lists/* && \
    apt-get clean && \
    apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends gnupg2 dirmngr ca-certificates && \
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 648ACFD622F3D138 || true && \
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 0E98404D386FA1D9 || true && \
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 605C66F00D6C9793 || true && \
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 8B48AD6246925553 || true && \
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys A379DEFFB3F1BB1E || true

# Update package lists after fixing GPG keys
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    libblas-dev \
    liblapack-dev \
    gfortran \
    wget \
    unzip \
    curl \
    ca-certificates \
    xvfb \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Add Google Chrome repository & install Chrome
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | tee /etc/apt/keyrings/google-chrome.asc > /dev/null && \
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.asc] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable

# Get Chrome version & set ChromeDriver version dynamically
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}') && \
    CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE") && \
    echo "Using ChromeDriver version: $CHROMEDRIVER_VERSION" && \
    wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip" && \
    unzip chromedriver_linux64.zip -d /usr/local/bin/ && \
    rm chromedriver_linux64.zip

# Set Environment Variables
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_BIN=/usr/local/bin/chromedriver
ENV DISPLAY=:99  

# Copy backend code
COPY . .

# Upgrade pip before installing requirements
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose Flask API port
EXPOSE 5001

# Start virtual framebuffer and backend
CMD ["bash", "-c", "Xvfb :99 -screen 0 1920x1080x16 & flask run --host=0.0.0.0 --port=5001"]