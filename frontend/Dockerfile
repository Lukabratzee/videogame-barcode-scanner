FROM python:3.11-slim

WORKDIR /app

# Install build tools and necessary libraries for pandas and numpy
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    libblas-dev \
    liblapack-dev \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt

# Install numpy first to avoid binary incompatibility issues
RUN pip install --no-cache-dir numpy && pip install --no-cache-dir pandas

# Install other dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "frontend.py", "--server.port=8501", "--server.address=0.0.0.0"]
