# Base image with Python and Chrome pre-installed
FROM selenium/standalone-chrome:latest

# Set working directory
WORKDIR /app

# Install Python and dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-venv \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Set environment variables for Chrome
ENV DISPLAY=:99

# Start virtual framebuffer (Xvfb) for rendering
RUN Xvfb :99 -screen 0 1920x1080x16 &

# Command to run the backend and frontend
CMD ["bash", "-c", "python3 backend/app.py & streamlit run frontend/frontend.py --server.port=8501 --server.address=0.0.0.0"]