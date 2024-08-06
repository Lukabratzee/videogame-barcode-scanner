#!/bin/bash

# Set project root directory (modify this path as needed)
PROJECT_ROOT="."

# Set paths to the frontend and backend directories
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_DIR="$PROJECT_ROOT/backend"

# Set the virtual environment directory
VENV_DIR="$PROJECT_ROOT/.venv"

# Function to set up virtual environment
setup_venv() {
  # Check if virtual environment directory exists
  if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
  else
    echo "Virtual environment already exists."
  fi

  # Activate the virtual environment
  source "$VENV_DIR/bin/activate"

  # Upgrade pip
  pip install --upgrade pip
}

# Function to install dependencies
install_dependencies() {
  # Install backend dependencies
  echo "Installing backend dependencies..."
  pip install -r "$BACKEND_DIR/requirements.txt"

  # Install frontend dependencies
  echo "Installing frontend dependencies..."
  pip install -r "$FRONTEND_DIR/requirements.txt"
}

# Function to run backend
run_backend() {
  echo "Starting backend..."
  cd "$BACKEND_DIR"
  python app.py &
  BACKEND_PID=$!
}

# Function to run frontend
run_frontend() {
  echo "Starting frontend..."
  cd .. && cd "$FRONTEND_DIR"
  streamlit run frontend.py &
  FRONTEND_PID=$!
}

# Main script execution
main() {
  echo "Setting up the environment and launching applications..."

  setup_venv
  install_dependencies
  run_backend
  run_frontend

  echo "Backend PID: $BACKEND_PID"
  echo "Frontend PID: $FRONTEND_PID"

  echo "Applications are running. Press Ctrl+C to stop."

  # Wait for frontend and backend processes to complete
  wait $BACKEND_PID
  wait $FRONTEND_PID
}

# Run the main function
main
