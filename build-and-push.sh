#!/bin/bash

# X86 Cross-Compile Build and Push Script for Video Game Catalogue
# Builds images specifically for AMD64 (x86) architecture for Portainer deployment

set -e

# Configuration
GITHUB_USERNAME="lukabratzee"  # Your GitHub username
REGISTRY="ghcr.io"
BACKEND_IMAGE="$REGISTRY/$GITHUB_USERNAME/video-game-catalogue-backend"
FRONTEND_IMAGE="$REGISTRY/$GITHUB_USERNAME/video-game-catalogue-frontend"
VERSION="${1:-latest}"
PLATFORM="linux/amd64"  # x86 only for Portainer

echo "🚀 Building and pushing Video Game Catalogue images (x86 for Portainer)"
echo "========================================================================"
echo "Registry: $REGISTRY"
echo "Username: $GITHUB_USERNAME"
echo "Version: $VERSION"
echo "Platform: $PLATFORM (x86 architecture)"
echo ""

# Check if logged in to registry
if ! docker info | grep -q "Username"; then
    echo "⚠️  Not logged in to Docker registry"
    echo "Please login first: docker login $REGISTRY"
    exit 1
fi

# Enable Docker buildx for cross-platform builds
echo "🔧 Setting up Docker buildx for x86 cross-compilation..."
docker buildx create --name x86-builder --driver docker-container --use 2>/dev/null || docker buildx use x86-builder
docker buildx inspect --bootstrap

# Function to build and push an x86 image
build_and_push() {
    local context=$1
    local image_name=$2
    local dockerfile="$context/Dockerfile"
    
    echo "🏗️ Building x86 $image_name:$VERSION..."
    
    # Build and push x86 image
    docker buildx build \
        -f "$dockerfile" \
        -t "$image_name:$VERSION" \
        -t "$image_name:latest" \
        --platform "$PLATFORM" \
        --build-arg VERSION="$VERSION" \
        --push \
        "$context"
    
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
