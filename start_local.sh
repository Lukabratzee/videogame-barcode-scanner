#!/bin/bash

# Video Game Catalogue - Simple Local Test (Fixed Version)
# Quick test setup for regional pricing feature

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🎮 Video Game Catalogue - Local Test (Fixed)${NC}"
echo "=============================================="

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating one...${NC}"
    python3 -m venv .venv
fi

# Activate virtual environment
echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
source .venv/bin/activate

# Install core dependencies only (skip problematic ones)
echo -e "${BLUE}📦 Installing core dependencies...${NC}"
pip install -q Flask==3.0.3 Werkzeug==3.0.3 streamlit==1.37.1 requests==2.32.3 selenium==4.23.1 undetected-chromedriver==3.5.5 webdriver-manager==4.0.2 setuptools==72.1.0 python-dotenv==1.0.0

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

# Kill any existing processes on our ports
echo -e "${BLUE}🔍 Cleaning up any existing processes...${NC}"
lsof -ti :5001 | xargs kill -9 2>/dev/null || true
lsof -ti :8501 | xargs kill -9 2>/dev/null || true
sleep 2

# Function to cleanup background processes
cleanup() {
    echo -e "\n${YELLOW}⚠️  Cleaning up...${NC}"
    lsof -ti :5001 | xargs kill -9 2>/dev/null || true
    lsof -ti :8501 | xargs kill -9 2>/dev/null || true
    exit 0
}

# Trap cleanup on script exit
trap cleanup SIGINT SIGTERM

# Initialize database
echo -e "${BLUE}🗃️  Initializing database...${NC}"
cd backend
python3 database_setup.py
cd ..

# Start backend in background with absolute path
echo -e "${BLUE}🚀 Starting backend server on port 5001...${NC}"
cd backend
export BACKEND_PORT=5001
export DATABASE_PATH="$(pwd)/../data/games.db"
echo "Database path: $DATABASE_PATH"
python3 app.py &
BACKEND_PID=$!
cd ..

# Wait for backend to be healthy
echo -e "${BLUE}🔍 Checking backend health...${NC}"
for i in {1..15}; do
    if curl -s http://localhost:5001/health 2>/dev/null | grep -q '"status": "healthy"'; then
        echo -e "${GREEN}✅ Backend is healthy!${NC}"
        break
    else
        echo -e "${YELLOW}⏳ Backend not ready yet (attempt $i/15)...${NC}"
        sleep 2
    fi
    if [ $i -eq 15 ]; then
        echo -e "${RED}❌ Backend failed to become healthy${NC}"
        echo "Backend response:"
        curl -s http://localhost:5001/health 2>/dev/null || echo "No response from backend"
        cleanup
    fi
done

# Start frontend
echo -e "${BLUE}🖥️  Starting frontend server on port 8501...${NC}"
cd frontend
export BACKEND_HOST=localhost
export BACKEND_PORT=5001
export FRONTEND_PORT=8501
streamlit run frontend.py --server.port=8501 --server.address=0.0.0.0 --browser.gatherUsageStats=false &
FRONTEND_PID=$!
cd ..

# Wait for frontend to be ready
echo -e "${BLUE}⏳ Waiting for frontend to be ready...${NC}"
sleep 5

echo -e "${GREEN}✅ Video Game Catalogue is running locally!${NC}"
echo ""
echo "🌐 Access the application at:"
echo -e "   Frontend: ${GREEN}http://localhost:8501${NC}"
echo -e "   Backend:  ${GREEN}http://localhost:5001${NC}"

echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}"

# Keep script running
wait
