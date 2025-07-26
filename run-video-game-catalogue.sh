#!/bin/bash

# Video Game Catalogue - Multi-Architecture Docker Setup
# This script contains everything needed to run the application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose-standalone.yml"
DATA_DIR="data"
CONFIG_DIR="config"

echo -e "${BLUE}🎮 Video Game Catalogue - Standalone Setup${NC}"
echo "=============================================="

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}⚠️  Cleaning up...${NC}"
    docker-compose -f "$COMPOSE_FILE" down 2>/dev/null || true
    exit 0
}

# Trap cleanup on script exit
trap cleanup SIGINT SIGTERM

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# Check for port conflicts and offer to kill conflicting processes
echo -e "${BLUE}🔍 Checking for port conflicts...${NC}"
conflicts=()
ports=(5001 8501)
for port in "${ports[@]}"; do
    if lsof -i ":$port" >/dev/null 2>&1; then
        conflicts+=($port)
        echo -e "${YELLOW}⚠️  Port $port is in use${NC}"
    fi
done

if [ ${#conflicts[@]} -gt 0 ]; then
    echo -e "${YELLOW}Port conflicts detected on: ${conflicts[*]}${NC}"
    echo "Would you like to stop conflicting processes? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        for port in "${conflicts[@]}"; do
            echo -e "${BLUE}🛑 Stopping processes on port $port...${NC}"
            pids=$(lsof -ti ":$port" 2>/dev/null || true)
            if [ -n "$pids" ]; then
                for pid in $pids; do
                    if kill "$pid" 2>/dev/null; then
                        echo -e "${GREEN}✅ Stopped process $pid on port $port${NC}"
                    else
                        echo -e "${YELLOW}⚠️  Could not stop process $pid (may require sudo)${NC}"
                    fi
                done
            fi
        done
    else
        echo -e "${RED}❌ Cannot start application with port conflicts. Please stop the conflicting processes manually.${NC}"
        exit 1
    fi
fi

# Check if docker-compose is available
if ! command -v docker-compose >/dev/null 2>&1; then
    echo -e "${RED}❌ docker-compose is not installed. Please install it and try again.${NC}"
    exit 1
fi

echo -e "${BLUE}📁 Creating required directories...${NC}"
mkdir -p "$DATA_DIR" "$CONFIG_DIR"

echo -e "${BLUE}⚙️  Creating configuration files...${NC}"

# Create config.json
cat > "$CONFIG_DIR/config.json" << 'EOF'
{
  "price_source": "eBay"
}
EOF

# Create docker-compose file
cat > "$COMPOSE_FILE" << 'EOF'
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
EOF

echo -e "${BLUE}🐳 Starting Video Game Catalogue...${NC}"
echo "This will pull the latest images and start the application."
echo ""

# Check if containers are already running
if docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
    echo -e "${YELLOW}⚠️  Application appears to be already running.${NC}"
    echo "Would you like to restart it? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}🔄 Restarting application...${NC}"
        docker-compose -f "$COMPOSE_FILE" down
    else
        echo -e "${GREEN}✅ Application is already running!${NC}"
        echo ""
        echo "🌐 Access the application at:"
        echo -e "   Frontend: ${GREEN}http://localhost:8501${NC}"
        echo -e "   Backend:  ${GREEN}http://localhost:5001${NC}"
        exit 0
    fi
fi

# Pull latest images
echo -e "${BLUE}📥 Pulling latest Docker images...${NC}"
docker-compose -f "$COMPOSE_FILE" pull

# Start the application
echo -e "${BLUE}🚀 Starting containers...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d

# Wait a moment for services to start
echo -e "${BLUE}⏳ Waiting for services to start...${NC}"
sleep 5

# Check if services are running
if docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
    echo -e "${GREEN}✅ Video Game Catalogue is running!${NC}"
    echo ""
    echo "🌐 Access the application at:"
    echo -e "   Frontend: ${GREEN}http://localhost:8501${NC}"
    echo -e "   Backend:  ${GREEN}http://localhost:5001${NC}"
    echo ""
    echo "📊 To view logs:"
    echo "   docker-compose -f $COMPOSE_FILE logs -f"
    echo ""
    echo "🛑 To stop the application:"
    echo "   docker-compose -f $COMPOSE_FILE down"
    echo ""
    echo -e "${YELLOW}Press Ctrl+C to stop the application and clean up${NC}"
    
    # Keep script running and show logs
    echo -e "${BLUE}📄 Showing application logs (Press Ctrl+C to stop):${NC}"
    docker-compose -f "$COMPOSE_FILE" logs -f
else
    echo -e "${RED}❌ Failed to start services. Check the logs:${NC}"
    docker-compose -f "$COMPOSE_FILE" logs
    docker-compose -f "$COMPOSE_FILE" down
    exit 1
fi
