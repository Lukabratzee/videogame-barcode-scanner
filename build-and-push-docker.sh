#!/bin/bash

# Video Game Catalogue - Docker Build and Push Script
# This script builds the Docker images from current source code and pushes them to the registry

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGISTRY_PREFIX="lukabratzee/video-game-catalogue"
BACKEND_IMAGE="${REGISTRY_PREFIX}-backend"
FRONTEND_IMAGE="${REGISTRY_PREFIX}-frontend"
DATE_TAG=$(date +%Y%m%d-%H%M)

echo -e "${BLUE}🐳 Video Game Catalogue - Docker Build & Push${NC}"
echo "=================================================="

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# Stop any running containers
echo -e "${BLUE}🛑 Stopping any running containers...${NC}"
docker-compose -f docker-compose-standalone.yml down 2>/dev/null || true

# Remove old images to force rebuild
echo -e "${BLUE}🗑️  Removing old local images...${NC}"
docker rmi ${BACKEND_IMAGE}:latest 2>/dev/null || true
docker rmi ${FRONTEND_IMAGE}:latest 2>/dev/null || true

# Build backend image
echo -e "${BLUE}🔨 Building backend image...${NC}"
docker build \
    --no-cache \
    --platform linux/amd64 \
    -f backend/Dockerfile \
    -t ${BACKEND_IMAGE}:latest \
    -t ${BACKEND_IMAGE}:${DATE_TAG} \
    .

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Backend build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Backend image built successfully${NC}"

# Build frontend image
echo -e "${BLUE}🔨 Building frontend image...${NC}"
docker build \
    --no-cache \
    --platform linux/amd64 \
    -f frontend/Dockerfile \
    -t ${FRONTEND_IMAGE}:latest \
    -t ${FRONTEND_IMAGE}:${DATE_TAG} \
    frontend/

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Frontend build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Frontend image built successfully${NC}"

# Push images to registry
echo -e "${BLUE}📤 Pushing images to Docker Hub...${NC}"

echo -e "${BLUE}📤 Pushing backend:latest...${NC}"
docker push ${BACKEND_IMAGE}:latest

echo -e "${BLUE}📤 Pushing backend:${DATE_TAG}...${NC}"
docker push ${BACKEND_IMAGE}:${DATE_TAG}

echo -e "${BLUE}📤 Pushing frontend:latest...${NC}"
docker push ${FRONTEND_IMAGE}:latest

echo -e "${BLUE}📤 Pushing frontend:${DATE_TAG}...${NC}"
docker push ${FRONTEND_IMAGE}:${DATE_TAG}

echo -e "${GREEN}✅ All images pushed successfully!${NC}"
echo ""
echo "🎯 Images built and pushed:"
echo -e "   Backend:  ${GREEN}${BACKEND_IMAGE}:latest${NC}"
echo -e "   Backend:  ${GREEN}${BACKEND_IMAGE}:${DATE_TAG}${NC}"
echo -e "   Frontend: ${GREEN}${FRONTEND_IMAGE}:latest${NC}"
echo -e "   Frontend: ${GREEN}${FRONTEND_IMAGE}:${DATE_TAG}${NC}"
echo ""
echo -e "${BLUE}🚀 Ready for deployment! Run your deployment script to use the updated images.${NC}"
