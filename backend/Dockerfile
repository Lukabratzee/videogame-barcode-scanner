# Use a slim Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install dependencies
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

# Add Google Chrome repository (New Signed Key Method)
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | tee /etc/apt/keyrings/google-chrome.asc > /dev/null && \
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.asc] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list

# Update package lists again & Install Chrome
RUN apt-get update && apt-get install -y google-chrome-stable

# Install ChromeDriver (Auto-match Chrome version)
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}') && \
    CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION") && \
    wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip" && \
    unzip chromedriver_linux64.zip -d /usr/local/bin/ && \
    rm chromedriver_linux64.zip

# Copy backend code
COPY . .

# Install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose Flask API port
EXPOSE 5001

# Set the Flask environment
ENV FLASK_ENV=development
ENV DISPLAY=:99  
# Set display for Xvfb

# Start virtual framebuffer and backend
CMD ["bash", "-c", "Xvfb :99 -screen 0 1920x1080x16 & flask run --host=0.0.0.0 --port=5001"]