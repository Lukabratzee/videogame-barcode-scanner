#!/bin/bash

# Video Game Catalogue - Local Development Startup
# This script runs the application locally for testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🎮 Video Game Catalogue - Local Development Mode${NC}"
echo "=============================================="

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating one...${NC}"
    python3 -m venv .venv
fi

# Activate virtual environment
echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
source .venv/bin/activate

# Check if dependencies are installed
echo -e "${BLUE}📦 Installing/updating dependencies...${NC}"
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt

# Check for port conflicts
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

# Create config directory and file if they don't exist
mkdir -p config data
if [ ! -f "config/config.json" ]; then
    echo -e "${BLUE}⚙️  Creating configuration file...${NC}"
    cat > config/config.json << 'EOF'
{
  "price_source": "PriceCharting"
}
EOF
fi

# Function to cleanup background processes
cleanup() {
    echo -e "\n${YELLOW}⚠️  Cleaning up...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    exit 0
}

# Trap cleanup on script exit
trap cleanup SIGINT SIGTERM

# Initialize database
echo -e "${BLUE}🗃️  Initializing database...${NC}"
cd backend
python3 database_setup.py
cd ..

# Start backend in background
echo -e "${BLUE}🚀 Starting backend server on port 5001...${NC}"
cd backend
export BACKEND_PORT=5001
export DATABASE_PATH="../data/games.db"
python3 app.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo -e "${BLUE}⏳ Waiting for backend to start...${NC}"
sleep 3

# Check if backend is running
if ! curl -s http://localhost:5001/health >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Backend may not be ready yet, continuing anyway...${NC}"
fi

# Start frontend
echo -e "${BLUE}🖥️  Starting frontend server on port 8501...${NC}"
cd frontend
export BACKEND_HOST=localhost
export BACKEND_PORT=5001
export FRONTEND_PORT=8501
streamlit run frontend.py --server.port=8501 --server.address=0.0.0.0 --browser.gatherUsageStats=false &
FRONTEND_PID=$!
cd ..

# Wait for services to be ready
echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"
sleep 5

echo -e "${GREEN}✅ Video Game Catalogue is running locally!${NC}"
echo ""
echo "🌐 Access the application at:"
echo -e "   Frontend: ${GREEN}http://localhost:8501${NC}"
echo -e "   Backend:  ${GREEN}http://localhost:5001${NC}"
echo ""
echo -e "${BLUE}🧪 Test the new PriceCharting region feature:${NC}"
echo "   1. Go to the frontend URL above"
echo "   2. In the sidebar, select 'PriceCharting' as Price Source"
echo "   3. You should see a 'PriceCharting Region' dropdown appear"
echo "   4. Try different regions (PAL, US, Japan) to see pricing differences"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}"

# Keep script running
wait
