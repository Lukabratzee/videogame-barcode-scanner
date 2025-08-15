#!/bin/bash

# Video Game Catalogue - Docker Build and Push Script
# This script builds the Docker images from current source code and pushes them to the registry
#
# Usage:
#   ./build-and-push-docker.sh                    # Use git branch as tag
#   ./build-and-push-docker.sh -tag dev           # Use custom tag 'dev'
#   ./build-and-push-docker.sh --tag feature-123  # Use custom tag 'feature-123'

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

# Parse command line arguments
CUSTOM_TAG=""
while [[ $# -gt 0 ]]; do
  case $1 in
    -tag|--tag)
      CUSTOM_TAG="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [-tag|--tag TAG_NAME]"
      echo ""
      echo "Examples:"
      echo "  $0                    # Use git branch as tag"
      echo "  $0 -tag dev           # Use custom tag 'dev'"
      echo "  $0 --tag feature-123  # Use custom tag 'feature-123'"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use -h or --help for usage information"
      exit 1
      ;;
  esac
done

# Determine tag to use
if [ -n "$CUSTOM_TAG" ]; then
    # Use custom tag provided by user
    # Sanitize: lowercase, replace invalid chars (anything not [a-z0-9._-]) with '-'
    MAIN_TAG=$(echo "$CUSTOM_TAG" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9._-]+/-/g')
    echo -e "${BLUE}🏷️  Using custom tag: ${GREEN}${CUSTOM_TAG}${NC} → sanitized: ${GREEN}${MAIN_TAG}${NC}"
    IS_MAIN_BRANCH=false
else
    # Use git branch as tag (existing behavior)
    GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "detached")
    # Sanitize: lowercase, replace invalid chars (anything not [a-z0-9._-]) with '-'
    MAIN_TAG=$(echo "$GIT_BRANCH" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9._-]+/-/g')
    echo -e "${BLUE}🔖 Git branch: ${GREEN}${GIT_BRANCH}${NC} → tag: ${GREEN}${MAIN_TAG}${NC}"
    IS_MAIN_BRANCH=$( [ "$MAIN_TAG" = "main" ] && echo true || echo false )
fi

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

# Remove old images to force rebuild of 'latest' (optional)
echo -e "${BLUE}🗑️  Removing old local images (optional)...${NC}"
docker rmi ${BACKEND_IMAGE}:latest 2>/dev/null || true
docker rmi ${FRONTEND_IMAGE}:latest 2>/dev/null || true

# Build backend image
echo -e "${BLUE}🔨 Building backend image...${NC}"
docker build \
    --no-cache \
    --platform linux/amd64 \
    -f backend/Dockerfile \
    -t ${BACKEND_IMAGE}:${DATE_TAG} \
    -t ${BACKEND_IMAGE}:${MAIN_TAG} \
    $( [ "$IS_MAIN_BRANCH" = "true" ] && echo -t ${BACKEND_IMAGE}:latest ) \
    $( [ "$IS_MAIN_BRANCH" = "true" ] && echo -t ${BACKEND_IMAGE}:main ) \
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
    -t ${FRONTEND_IMAGE}:${DATE_TAG} \
    -t ${FRONTEND_IMAGE}:${MAIN_TAG} \
    $( [ "$IS_MAIN_BRANCH" = "true" ] && echo -t ${FRONTEND_IMAGE}:latest ) \
    $( [ "$IS_MAIN_BRANCH" = "true" ] && echo -t ${FRONTEND_IMAGE}:main ) \
    frontend/

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Frontend build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Frontend image built successfully${NC}"

# Push images to registry
echo -e "${BLUE}📤 Pushing images to Docker Hub...${NC}"

echo -e "${BLUE}📤 Pushing backend:${DATE_TAG}...${NC}"
docker push ${BACKEND_IMAGE}:${DATE_TAG}
echo -e "${BLUE}📤 Pushing backend:${MAIN_TAG}...${NC}"
docker push ${BACKEND_IMAGE}:${MAIN_TAG}
if [ "$IS_MAIN_BRANCH" = "true" ]; then
  echo -e "${BLUE}📤 Pushing backend:main and backend:latest...${NC}"
  docker push ${BACKEND_IMAGE}:main
  docker push ${BACKEND_IMAGE}:latest
fi

echo -e "${BLUE}📤 Pushing frontend:${DATE_TAG}...${NC}"
docker push ${FRONTEND_IMAGE}:${DATE_TAG}
echo -e "${BLUE}📤 Pushing frontend:${MAIN_TAG}...${NC}"
docker push ${FRONTEND_IMAGE}:${MAIN_TAG}
if [ "$IS_MAIN_BRANCH" = "true" ]; then
  echo -e "${BLUE}📤 Pushing frontend:main and frontend:latest...${NC}"
  docker push ${FRONTEND_IMAGE}:main
  docker push ${FRONTEND_IMAGE}:latest
fi

echo -e "${GREEN}✅ All images pushed successfully!${NC}"
echo ""
echo "🎯 Images built and pushed:"
echo -e "   Backend:  ${GREEN}${BACKEND_IMAGE}:${DATE_TAG}${NC}"
echo -e "   Backend:  ${GREEN}${BACKEND_IMAGE}:${MAIN_TAG}${NC}"
if [ "$IS_MAIN_BRANCH" = "true" ]; then
  echo -e "   Backend:  ${GREEN}${BACKEND_IMAGE}:main${NC}"
  echo -e "   Backend:  ${GREEN}${BACKEND_IMAGE}:latest${NC}"
fi
echo -e "   Frontend: ${GREEN}${FRONTEND_IMAGE}:${DATE_TAG}${NC}"
echo -e "   Frontend: ${GREEN}${FRONTEND_IMAGE}:${MAIN_TAG}${NC}"
if [ "$IS_MAIN_BRANCH" = "true" ]; then
  echo -e "   Frontend: ${GREEN}${FRONTEND_IMAGE}:main${NC}"
  echo -e "   Frontend: ${GREEN}${FRONTEND_IMAGE}:latest${NC}"
fi
echo ""
echo -e "${BLUE}🚀 Ready for deployment! Run your deployment script to use the updated images.${NC}"
