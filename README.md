
# Video Game Catalogue

This project is a web application for cataloging video games. It includes a frontend built with Streamlit and a backend powered by Flask. The application allows users to view, add, edit, and delete game entries, as well as filter games by various criteria. Additionally, it supports searching for games by name and adding them via an iOS Shortcut.

## Features

- **Game Listing**: View a list of video games with detailed information.
- **Add Games**: Add new games manually or by searching for game names.
- **Edit Games**: Update existing game details.
- **Delete Games**: Remove games from the catalogue.
- **Search and Filter**: Search for games by name and filter by various attributes.
- **iOS Shortcut Integration**: Use an iOS Shortcut to scan games and add them to the catalogue.

## Setup and Installation

### 1. Running with Docker

The recommended way to run the application is using Docker and Docker Compose. This setup ensures all dependencies are correctly managed and provides an easy way to deploy the application.

#### Prerequisites

- Docker
- Docker Compose

#### Instructions

1. **Clone the Repository**

   ```sh
   git clone 192.168.1.111:3000/lukabratzee/video-game-catalogue
   cd video-game-catalogue
   ```

2. **Build and Start the Services**

   Use Docker Compose to build the Docker images and start the frontend and backend services.

   ```sh
   docker-compose up --build
   ```

   This command will:

   - Build Docker images for both the frontend and backend services.
   - Start the containers, exposing the frontend on `http://localhost:8501` and the backend on `http://localhost:5001`.

3. **Access the Application**

   - **Frontend**: Open your web browser and navigate to `http://localhost:8501`.
   - **Backend**: The backend service is accessible at `http://localhost:5001`.

### 2. Running Locally (Without Docker)

To run the application without Docker, you'll need to set up a virtual environment and install the dependencies for both the frontend and backend.

#### Prerequisites

- Python 3.11
- Virtualenv

#### Instructions

1. **Set Up Virtual Environment**

   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install Dependencies**

   - **Frontend**:
     ```sh
     cd frontend
     pip install -r requirements.txt
     ```

   - **Backend**:
     ```sh
     cd backend
     pip install -r requirements.txt
     ```

3. **Run the Application**

   - **Frontend**:
     ```sh
     streamlit run frontend/frontend.py
     ```

   - **Backend**:
     ```sh
     python backend/app.py
     ```

   By default, the frontend will be accessible at `http://localhost:8501` and the backend at `http://localhost:5001`.

## iOS Shortcut

To use the iOS Shortcut for scanning games, you can add the provided shortcut to your iPhone:

[iOS Shortcut Link](https://www.icloud.com/shortcuts/b324cde379434401a511e025ee9ccd4c)

This shortcut allows you to scan games and send the data to the application for adding to the catalogue.
Remember to change the IP's in the shortcut to IP running the application.
## FAQ

## CHROMEDRIVER 114 VERSION NO WORKY

Define where Chromedriver is `i.e /opt/homebrew/bin/chromedriver`
Run this: `bashpip uninstall undetected-chromedriver webdriver-manager`
`pip install undetected-chromedriver webdriver-manager`
