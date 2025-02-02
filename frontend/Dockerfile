# ------------------------------------------
# Dockerfile: Streamlit + Selenium + Xvfb
# ------------------------------------------
    FROM selenium/standalone-chrome:latest

    # We need root privileges to install packages
    USER root
    
    # Create /app as our working directory
    WORKDIR /app
    
    # 1) Install Python, pip, venv, and Xvfb
    RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-venv python3-pip xvfb \
        && rm -rf /var/lib/apt/lists/*
    
    # 2) Create a Python virtual environment
    RUN python3 -m venv /venv --copies
    
    # Make sure venv is first in PATH
    ENV PATH="/venv/bin:$PATH"
    
    # 3) Copy in our requirements and install them
    COPY requirements.txt /app/requirements.txt
    RUN pip install --no-cache-dir --upgrade pip
    RUN pip install --no-cache-dir -r requirements.txt
    
    # 4) Copy your local frontend code (including .streamlit/config.toml) into /app
    #    So if you have /root/docker/video_game_catalogue/frontend/.streamlit/config.toml
    #    it will become /app/.streamlit/config.toml in the container.
    COPY . /app
    
    # 5) Make sure there's a ~/.streamlit folder inside the container's root
    #    If you already have /app/.streamlit/config.toml, we copy it to /root/.streamlit/config.toml
    RUN mkdir -p /root/.streamlit
    RUN cp -r /app/.streamlit /root/ || true
    
    # 6) Xvfb needs DISPLAY set
    ENV DISPLAY=:99
    
    # 7) Command: remove stale lock, start Xvfb, then Streamlit
    CMD ["/bin/bash", "-c", "rm -f /tmp/.X99-lock && Xvfb :99 -screen 0 1920x1080x16 & \
        streamlit run /app/frontend.py --server.port=8501 --server.address=0.0.0.0"]