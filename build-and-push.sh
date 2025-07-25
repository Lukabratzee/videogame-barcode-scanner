#!/bin/bash

# Manual Build and Push Script for Video Game Catalogue
# Use this if you want to build and push images manually instead of using GitHub Actions

set -e

# Configuration
GITHUB_USERNAME="lukabratzee"  # Your GitHub username
REGISTRY="ghcr.io"
BACKEND_IMAGE="$REGISTRY/$GITHUB_USERNAME/video-game-catalogue-backend"
FRONTEND_IMAGE="$REGISTRY/$GITHUB_USERNAME/video-game-catalogue-frontend"
VERSION="${1:-latest}"

echo "🚀 Building and pushing Video Game Catalogue images"
echo "=================================================="
echo "Registry: $REGISTRY"
echo "Username: $GITHUB_USERNAME"
echo "Version: $VERSION"
echo ""

# Check if logged in to registry
if ! docker info | grep -q "Username"; then
    echo "⚠️  Not logged in to Docker registry"
    echo "Please login first: docker login $REGISTRY"
    exit 1
fi

# Function to build and push an image
build_and_push() {
    local context=$1
    local image_name=$2
    local dockerfile="$context/Dockerfile"
    
    echo "🏗️ Building $image_name:$VERSION..."
    
    # Build with build context including modules
    docker build \
        -f "$dockerfile" \
        -t "$image_name:$VERSION" \
        -t "$image_name:latest" \
        --build-arg VERSION="$VERSION" \
        "$context"
    
    echo "📤 Pushing $image_name:$VERSION..."
    docker push "$image_name:$VERSION"
    
    if [ "$VERSION" != "latest" ]; then
        echo "📤 Pushing $image_name:latest..."
        docker push "$image_name:latest"
    fi
    
    echo "✅ Successfully built and pushed $image_name"
    echo ""
}

# Build context setup - copy modules to each directory temporarily
echo "📋 Preparing build contexts..."

# Copy modules to backend
cp -r ./modules ./backend/modules

# Copy modules to frontend  
cp -r ./modules ./frontend/modules

# Build and push backend
build_and_push "./backend" "$BACKEND_IMAGE"

# Build and push frontend
build_and_push "./frontend" "$FRONTEND_IMAGE"

# Cleanup - remove copied modules
echo "🧹 Cleaning up build contexts..."
rm -rf ./backend/modules
rm -rf ./frontend/modules

echo "🎉 All images built and pushed successfully!"
echo ""
echo "📋 Image URLs:"
echo "   Backend:  $BACKEND_IMAGE:$VERSION"
echo "   Frontend: $FRONTEND_IMAGE:$VERSION"
echo ""
echo "🔧 Update your docker-compose.yml with these image names"
echo "💡 Tip: Use 'docker pull' on your Portainer host to get the latest images"
