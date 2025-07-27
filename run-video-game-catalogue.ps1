# Video Game Catalogue - Multi-Architecture Docker Setup (PowerShell)
# This script contains everything needed to run the application

param(
    [switch]$Stop
)

# Configuration
$ComposeFile = "docker-compose-standalone.yml"
$DataDir = "data"
$ConfigDir = "config"

# Colors for output
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Green($message) { Write-ColorOutput Green $message }
function Write-Red($message) { Write-ColorOutput Red $message }
function Write-Yellow($message) { Write-ColorOutput Yellow $message }
function Write-Blue($message) { Write-ColorOutput Blue $message }

Write-Blue "Video Game Catalogue - Standalone Setup"
Write-Output "=============================================="

# Cleanup function
function Cleanup {
    Write-Yellow "`nCleaning up..."
    try {
        docker-compose -f $ComposeFile down 2>$null
    } catch {
        # Ignore errors during cleanup
    }
    exit 0
}

# Handle Ctrl+C
$null = Register-EngineEvent PowerShell.Exiting -Action { Cleanup }

# If stop parameter is provided, just stop and exit
if ($Stop) {
    Write-Yellow "Stopping Video Game Catalogue..."
    try {
        docker-compose -f $ComposeFile down
        Write-Green "Application stopped successfully"
    } catch {
        Write-Red "Error stopping application: $_"
    }
    exit 0
}

# Check if Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Red "Docker is not running. Please start Docker and try again."
    exit 1
}

# Check for port conflicts and offer to kill conflicting processes
Write-Blue "Checking for port conflicts..."
$conflicts = @()
$ports = @(5001, 8501)
foreach ($port in $ports) {
    $processes = netstat -ano | Select-String ":$port " | Select-String "LISTENING"
    if ($processes) {
        $conflicts += $port
        Write-Yellow "Port $port is in use"
    }
}

if ($conflicts.Count -gt 0) {
    Write-Yellow "Port conflicts detected on: $($conflicts -join ', ')"
    $response = Read-Host "Would you like to stop conflicting processes? (y/N)"
    if ($response -match "^[Yy]$") {
        foreach ($port in $conflicts) {
            Write-Blue "Stopping processes on port $port..."
            $processes = netstat -ano | Select-String ":$port " | Select-String "LISTENING"
            foreach ($process in $processes) {
                $processId = ($process -split '\s+')[-1]
                try {
                    Stop-Process -Id $processId -Force
                    Write-Green "Stopped process $processId on port $port"
                } catch {
                    Write-Yellow "Could not stop process $processId (may require admin rights)"
                }
            }
        }
    } else {
        Write-Red "Cannot start application with port conflicts. Please stop the conflicting processes manually."
        exit 1
    }
}

# Check if docker-compose is available
try {
    docker-compose --version | Out-Null
} catch {
    Write-Red "docker-compose is not installed. Please install it and try again."
    exit 1
}

Write-Blue "Creating required directories..."
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null

Write-Blue "Creating configuration files..."

# Create config.json
$configContent = @"
{
  "price_source": "PriceCharting"
}
"@
$configContent | Out-File -FilePath "$ConfigDir\config.json" -Encoding UTF8

# Create docker-compose file
$composeContent = @"
services:
  backend:
    image: lukabratzee/video-game-catalogue-backend:latest
    pull_policy: always
    platform: linux/amd64
    container_name: video-game-catalogue-backend
    ports:
      - "5001:5001"
    environment:
      - DATABASE_PATH=/app/data/games.db
      - BACKEND_PORT=5001
    volumes:
      - ./data:/app/data
      - ./config:/app/config
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETUID
      - SETGID
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
    restart: unless-stopped

  frontend:
    image: lukabratzee/video-game-catalogue-frontend:latest
    pull_policy: always
    platform: linux/amd64
    container_name: video-game-catalogue-frontend
    ports:
      - "8501:8501"
    environment:
      - BACKEND_HOST=backend
      - BACKEND_PORT=5001
      - FRONTEND_PORT=8501
    depends_on:
      backend:
        condition: service_healthy
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
    restart: unless-stopped

volumes:
  data:
    driver: local
  config:
    driver: local

networks:
  default:
    driver: bridge
"@
$composeContent | Out-File -FilePath $ComposeFile -Encoding UTF8

Write-Blue "Starting Video Game Catalogue..."
Write-Output "This will pull the latest images and start the application."
Write-Output ""

# Check if containers are already running
$runningCheck = docker-compose -f $ComposeFile ps | Select-String "Up"
if ($runningCheck) {
    Write-Yellow "Application appears to be already running."
    $response = Read-Host "Would you like to restart it? (y/N)"
    if ($response -match "^[Yy]$") {
        Write-Blue "Restarting application..."
        docker-compose -f $ComposeFile down
    } else {
        Write-Green "Application is already running!"
        Write-Output ""
        Write-Output "Access the application at:"
        Write-Green "   Frontend: http://localhost:8501"
        Write-Green "   Backend:  http://localhost:5001"
        exit 0
    }
}

# Pull latest images
Write-Blue "Pulling latest Docker images..."
try {
    docker-compose -f $ComposeFile pull
} catch {
    Write-Red "Failed to pull images: $_"
    exit 1
}

# Start the application
Write-Blue "Starting containers..."
try {
    docker-compose -f $ComposeFile up -d
} catch {
    Write-Red "Failed to start containers: $_"
    exit 1
}

# Wait a moment for services to start
Write-Blue "Waiting for services to start..."
Start-Sleep -Seconds 5

# Check if services are running
$runningServices = docker-compose -f $ComposeFile ps | Select-String "Up"
if ($runningServices) {
    Write-Green "Video Game Catalogue is running!"
    Write-Output ""
    Write-Output "Access the application at:"
    Write-Green "   Frontend: http://localhost:8501"
    Write-Green "   Backend:  http://localhost:5001"
    Write-Output ""
    Write-Output "To view logs:"
    Write-Output "   docker-compose -f $ComposeFile logs -f"
    Write-Output ""
    Write-Output "To stop the application:"
    Write-Output "   .\run-video-game-catalogue.ps1 -Stop"
    Write-Output "   or: docker-compose -f $ComposeFile down"
    Write-Output ""
    Write-Yellow "Press Ctrl+C to stop the application and clean up"
    
    # Keep script running and show logs
    Write-Blue "Showing application logs (Press Ctrl+C to stop):"
    try {
        docker-compose -f $ComposeFile logs -f
    } catch {
        Write-Yellow "Log streaming interrupted"
        Cleanup
    }
} else {
    Write-Red "Failed to start services. Check the logs:"
    docker-compose -f $ComposeFile logs
    docker-compose -f $ComposeFile down
    exit 1
}
