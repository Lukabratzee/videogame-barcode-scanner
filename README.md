# Video Game Catalogue

A comprehensive web application for cataloging and managing your video game collection. This project features a user-friendly frontend built with Streamlit and a robust backend powered by Flask, enabling users to easily track, search, and value their game library.

## 🌟 Key Features

- **Game Management**: View, add, edit, and delete game entries with detailed information.
- **Smart Search & Filtering**: Search for games by name, and filter by publisher, platform, genre, or release year.
- **IGDB Integration**: Fetch detailed game information, including cover art, descriptions, and release dates, from the Internet Game Database (IGDB).
- **Price Scraping**: Automatically scrape current prices from eBay, Amazon, or CeX to track the value of your games.
- **iOS Shortcut Support**: Use an iOS Shortcut to scan game barcodes and quickly add them to your catalogue.
- **Data Export**: Export your game collection to a CSV file for backup or analysis.
- **Multi-Architecture Support**: Docker images built for both AMD64 (x86) and ARM64 architectures, ensuring compatibility across various systems.
- **Persistent Storage**: Data is stored locally in a SQLite database, ensuring your collection is preserved between sessions.
- **Integrated Music Player**: Enjoy video game music while browsing your collection with the embedded VIPVGM player.

## 🏗️ Project Structure

```
video-game-catalogue/
├── backend/                 # Flask API backend
│   ├── app.py              # Main application logic, API endpoints
│   ├── requirements.txt    # Python dependencies for the backend
│   ├── Dockerfile          # Docker configuration for the backend
│   └── ...                 # Other backend-related files
├── frontend/               # Streamlit web frontend
│   ├── frontend.py         # Main Streamlit application
│   ├── requirements.txt    # Python dependencies for the frontend
│   ├── Dockerfile          # Docker configuration for the frontend
│   └── modules/
│       └── scrapers.py    # Web scraping logic for prices
├── config/                 # Configuration files directory
│   └── config.json        # Application configuration (e.g., price source)
├── data/                   # Data persistence directory
│   └── games.db            # SQLite database (created automatically)
├── .env                    # Environment variables (e.g., database path)
├── docker-compose-ghcr.yml # Docker Compose for GitHub Container Registry
├── docker-compose-standalone.yml # Docker Compose for standalone setup
├── run-video-game-catalogue.sh   # Bash script for easy setup
├── run-video-game-catalogue.ps1  # PowerShell script for easy setup
└── README.md               # This file
```

## 🚀 Setup and Installation

### Prerequisites

- **Docker** and **Docker Compose** (for the recommended Docker setup)
- **Python 3.11** (for local development without Docker)
- **Git** (to clone the repository)

### Option 1: Running with Docker (Recommended)

This is the easiest and most reliable way to get the application running. It uses pre-built Docker images and handles all dependencies automatically.

#### Quick Start (One-Command Setup)

For your convenience, standalone scripts are provided to set up and run the application with a single command.

**For Mac/Linux users:**
```bash
curl -O https://raw.githubusercontent.com/lukabratzee/video-game-catalogue/main/run-video-game-catalogue.sh
chmod +x run-video-game-catalogue.sh
./run-video-game-catalogue.sh
```

**For Windows users:**
```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/lukabratzee/video-game-catalogue/main/run-video-game-catalogue.ps1" -OutFile "run-video-game-catalogue.ps1"
.\run-video-game-catalogue.ps1
```

These scripts will:
- Create the necessary `data/` and `config/` directories.
- Generate a `docker-compose-standalone.yml` file.
- Pull the latest multi-architecture Docker images.
- Start the frontend and backend services.
- Display real-time application logs.

#### Manual Docker Setup

1.  **Clone the Repository**
    ```sh
    git clone 192.168.1.111:3000/lukabratzee/video-game-catalogue
    cd video-game-catalogue
    ```

2.  **Using GitHub Container Registry (ghcr)**
    This method pulls pre-built images.
    ```sh
    docker-compose -f docker-compose-ghcr.yml up -d
    ```

3.  **Access the Application**
    - **Frontend**: Open your web browser and navigate to `http://localhost:8501`
    - **Backend API**: The backend service is accessible at `http://localhost:5001`
    - **Health Check**: You can check the status of the backend at `http://localhost:5001/health`

### Option 2: Running Locally (Without Docker)

This method is suitable for developers who want to modify the source code or run the application in their native Python environment.

1.  **Clone the Repository**
    ```sh
    git clone 192.168.1.111:3000/lukabratzee/video-game-catalogue
    cd video-game-catalogue
    ```

2.  **Set Up Environment**
    - Create a `.env` file in the root directory and specify the database path. For example:
        ```
        DATABASE_PATH=data/games.db
        ```
    - It's recommended to use a virtual environment:
        ```sh
        python3 -m venv .venv
        source .venv/bin/activate  # On Windows: .venv\Scripts\activate
        ```

3.  **Install Dependencies**
    - **Backend**:
        ```sh
        cd backend
        pip install -r requirements.txt
        ```
    - **Frontend**:
        ```sh
        cd ../frontend
        pip install -r requirements.txt
        ```

4.  **Database Setup**
    - The application will automatically create the SQLite database file at the path specified in your `.env` file when it first tries to access it.
    - You can manually run the database setup script if needed:
        ```sh
        cd backend
        python database_setup.py
        ```

5.  **Run the Application**
    - You need to run both the frontend and backend simultaneously in separate terminal windows.
    - **Backend** (in one terminal):
        ```sh
        cd backend
        python app.py
        ```
    - **Frontend** (in another terminal):
        ```sh
        cd frontend
        streamlit run frontend.py
        ```
    - Access the frontend at `http://localhost:8501`.

## 📖 User Guide

### Navigating the Interface

- **Home Page**: Displays your entire game collection, the total value of all games, and the top 5 most valuable games in your catalogue.
- **Sidebar**: Contains all the main tools for managing your collection:
    - **Home Button**: Resets all filters and returns you to the main view.
    - **Music Player**: An embedded player for video game music from VIPVGM.
    - **Price Scraping Settings**: Select your preferred price source (eBay, Amazon, or CeX) for automatic price lookups.
    - **Filter Games**: Search for games by title.
    - **Add Game**: Manually add a new game to your collection by entering its details.
    - **Delete Game**: Remove a game by its ID.
    - **Edit Game**: Modify an existing game's details by fetching it with its ID.
    - **Advanced Filters**: Apply complex filters (by publisher, platform, genre, year) and sort options. You can also export the filtered results to a CSV file.

### Adding Games

There are several ways to add games to your catalogue:

1.  **Manual Entry**:
    - Use the "Add Game" section in the sidebar.
    - Fill in the details like title, cover image URL, description, publisher, platforms, genres, and release date.
    - Click "Add Game".

2.  **IGDB Search by Name**:
    - In the main panel, find the "IGDB: Search Game by Name" section.
    - Enter a game name and click "Search Game".
    - The application will present an exact match and alternative matches from IGDB.
    - Select a game from the list.
    - Choose the correct platform from the dropdown.
    - Click "Add Selected Game". The application will automatically fetch the price from your selected source.

3.  **IGDB Search by ID**:
    - If you know the IGDB ID of a game, you can use the "IGDB: Search Game by ID" section.
    - Enter the ID and click "Search Game by ID".
    - After the game details are fetched, select the platform and click "Add Game by ID".

4.  **iOS Shortcut (Barcode Scanning)**:
    - Install the provided iOS Shortcuts on your iPhone.
        - [Primary Shortcut](https://www.icloud.com/shortcuts/024bf54a6f584cc78c3ed394bcda8e84)
        - [Alternate Shortcut](https://www.icloud.com/shortcuts/bea9f60437194f0fad2f89b87c9d1fff)
    - **Important**: You must edit the shortcut to point to your application's backend IP address (e.g., `http://YOUR_BACKEND_IP:5001/scan`).
    - Run the shortcut, scan a barcode, and it will send the data to the backend.
    - The application will look up the game and present you with options to add it to your database, similar to the IGDB search flow.

### Managing Your Collection

- **Viewing Games**: Your games are displayed on the home page. You can use the search and filter options in the sidebar to find specific games.
- **Editing Games**:
    - **Inline Edit**: On any game's display card, click the "Edit" button. An edit form will appear inline, allowing you to modify all details.
    - **Sidebar Edit**: Use the "Edit Game" section in the sidebar. Enter the game's ID, click "Fetch Game Details", modify the fields, and then click "Update Game".
- **Deleting Games**:
    - **Inline Delete**: On any game's display card, click the "Delete" button. You will be asked to confirm the action.
    - **Bulk Delete (Advanced Filters)**: When using "Advanced Filters", you can enable "Bulk Delete Mode". This allows you to select multiple games with checkboxes and delete them all at once.
    - **Sidebar Delete**: Use the "Delete Game" section in the sidebar. Enter the game's ID, confirm your intention with the checkbox, and click "Delete Game".
- **Exporting Data**:
    - From the "Advanced Filters" section in the sidebar, you can export your currently filtered view (or the entire collection if no filters are active) to a CSV file by clicking "Export Filtered CSV".
    - There is also a dedicated "Export All Games" section in the sidebar for exporting the entire database.

### Price Scraping

- The application can automatically scrape prices from eBay, Amazon, or CeX when adding games.
- You can set your preferred price source globally in the "Price Scraping Settings" in the sidebar. This selection will be used for all subsequent price lookups.
- The backend stores this preference, so it persists even if you restart the application.

## 🛠️ Configuration

### Environment Variables (`.env` file)

- `DATABASE_PATH`: Specifies the location of the SQLite database file. Example: `data/games.db`. This path is relative to the project root.

### Application Configuration (`config/config.json`)

This file is automatically generated and managed by the application. It stores user preferences such as:
- `price_source`: The default source for price scraping (`"eBay"`, `"Amazon"`, or `"CeX"`).

You generally do not need to edit this file manually, as the application provides UI controls to manage these settings.

## 🎨 Artwork Management

The application can automatically fetch high-resolution artwork from SteamGridDB, but you can also manually add artwork for games.

### Automatic Artwork Fetching

1. **Configure SteamGridDB API Key**: Get a free API key from [SteamGridDB](https://www.steamgriddb.com/profile/preferences/api)
2. **Add to Config**: Place your API key in `config/config.json`:
   ```json
   {
     "price_source": "PriceCharting",
     "steamgriddb_api_key": "your_actual_api_key_here"
   }
   ```
3. **Use the Editor**: In the sidebar, use "Update Game Artwork" to fetch artwork for specific games

### Manual Artwork Installation

If automatic fetching fails or you prefer custom artwork, you can manually add images:

1. **Download artwork** from [SteamGridDB](https://www.steamgriddb.com/) or any source
2. **Rename files** using the following convention:
   - **Grid Cover**: `<game_id>_grid.png` (e.g., `1234_grid.png`)
   - **Hero Image**: `<game_id>_hero.png` (e.g., `1234_hero.png`) 
   - **Logo**: `<game_id>_logo.png` (e.g., `1234_logo.png`)
   - **Icon**: `<game_id>_icon.png` (e.g., `1234_icon.png`)
3. **Place files** in the `data/artwork/` directory
4. **Restart the application** - it will automatically detect and use the new artwork

#### Artwork File Types

- **Grid Cover**: Square or portrait game cover (600x900px recommended)
- **Hero Image**: Wide banner image (1920x620px recommended)
- **Logo**: Game logo with transparent background (PNG recommended)
- **Icon**: Small square icon (256x256px recommended)

#### Finding Game IDs

- **In Gallery**: The Game ID is displayed on each game tile
- **In Editor**: View any game to see its ID in the "Game Information" section
- **In Database**: Check the `id` column in the games table

**Note**: Manual artwork takes precedence over automatically fetched artwork. If you place a manual file, it will be used instead of the SteamGridDB version.

## 🐳 Docker Details

### Images

The application uses Docker images hosted on GitHub Container Registry (ghcr.io):
- `ghcr.io/lukabratzee/video-game-catalogue-frontend`
- `ghcr.io/lukabratzee/video-game-catalogue-backend`

These images are built for both `AMD64` (Intel/AMD) and `ARM64` (Apple Silicon, ARM) architectures.

### Volumes

- `./data:/app/data`: Persists the SQLite database.
- `./config:/app/config`: Persists the application configuration file.

### Ports

- `8501:8501`: Exposes the Streamlit frontend.
- `5001:5001`: Exposes the Flask backend API.

## ⚠️ Troubleshooting & FAQ

### **ChromeDriver/Selenium Issues (Price Scraping)**

Price scraping relies on Selenium and ChromeDriver. Sometimes, version incompatibilities can arise.

- **Error**: `ChromeOptions error` or issues with `undetected-chromedriver`.
- **Solution**:
    1.  Ensure you have the latest version of Google Chrome installed.
    2.  In your local environment (not Docker), try reinstalling the relevant Python packages:
        ```sh
        pip uninstall -y selenium undetected-chromedriver webdriver-manager
        pip install selenium==4.23.1 undetected-chromedriver==3.5.5 webdriver-manager==4.0.2
        ```
    3.  The Docker images are configured with compatible versions, so this issue is less likely when using Docker.

### **Application is not accessible after running the script**

- **Check Docker**: Ensure Docker Desktop is running.
- **Check Ports**: Verify that ports `5001` and `8501` are not being used by other applications.
- **Check Logs**: View the container logs for errors:
    ```sh
    docker-compose -f docker-compose-standalone.yml logs
    ```

### **iOS Shortcut is not working**

- **IP Address**: The most common issue is an incorrect IP address in the shortcut. Make sure you have updated it to the IP address of the machine running the `backend` service.
- **Network**: Ensure your iPhone is on the same network as the machine running the application.
- **Backend Health**: Check that the backend is running and accessible at `http://YOUR_BACKEND_IP:5001/health`.

### **Database errors on startup**

- **Permissions**: Ensure the application has write permissions in the `data/` directory.
- **`.env` file**: Double-check that the `DATABASE_PATH` in your `.env` file is correct and that the directory for the database file exists.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

This project is licensed under a custom license - see the [LICENSE](LICENSE) file for details. (Note: A `LICENSE` file was not found in the provided file structure, you may need to add one).

## 🙏 Acknowledgments

- **IGDB (Internet Game Database)**: For providing the comprehensive game data API.
- **Streamlit**: For the powerful and easy-to-use frontend framework.
- **Flask**: For the lightweight and flexible backend framework.
- **VIPVGM**: For the awesome video game music stream.
