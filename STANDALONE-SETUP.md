# Video Game Catalogue - Standalone Docker Setup

These scripts provide a complete, self-contained way to run the Video Game Catalogue application using Docker with multi-architecture support.

## Prerequisites

- Docker installed and running
- docker-compose installed

## Quick Start

### Linux/macOS (Bash)

```bash
# Make the script executable (first time only)
chmod +x run-video-game-catalogue.sh

# Run the application
./run-video-game-catalogue.sh
```

### Windows (PowerShell)

```powershell
# Run the application
.\run-video-game-catalogue.ps1

# To stop the application
.\run-video-game-catalogue.ps1 -Stop
```

## What the scripts do

1. **Create required directories**: `data/` and `config/`
2. **Generate configuration**: Creates `config/config.json` with default settings
3. **Generate Docker Compose file**: Creates `docker-compose-standalone.yml` with complete configuration
4. **Pull latest images**: Downloads the latest multi-architecture Docker images from Docker Hub
5. **Start services**: Runs the backend and frontend containers
6. **Show logs**: Displays real-time application logs

## Access the application

Once running, you can access:

- **Frontend**: http://localhost:8501 (Streamlit web interface)
- **Backend**: http://localhost:5001 (Flask API)

## Stopping the application

- **Bash**: Press `Ctrl+C` in the terminal running the script
- **PowerShell**: Press `Ctrl+C` or run `.\run-video-game-catalogue.ps1 -Stop`
- **Manual**: `docker-compose -f docker-compose-standalone.yml down`

## Features

- ✅ Multi-architecture support (ARM64/AMD64)
- ✅ Automatic image pulling
- ✅ Health checks
- ✅ Security hardening
- ✅ Persistent data storage
- ✅ Self-contained configuration
- ✅ Colored output and progress indicators

## Troubleshooting

If you encounter issues:

1. **Check Docker is running**: `docker info`
2. **View logs**: `docker-compose -f docker-compose-standalone.yml logs`
3. **Restart**: Stop the application and run the script again
4. **Clean up**: `docker-compose -f docker-compose-standalone.yml down -v` (removes volumes too)

## File Structure

After running, you'll have:

```
.
├── run-video-game-catalogue.sh     # Bash script
├── run-video-game-catalogue.ps1    # PowerShell script
├── docker-compose-standalone.yml   # Generated Docker Compose file
├── data/                           # Database storage (persistent)
│   └── games.db                    # SQLite database (created automatically)
└── config/                         # Configuration files
    └── config.json                 # Application configuration
```

The `data/` directory persists your game database between runs, so your data won't be lost when you stop and restart the application.
