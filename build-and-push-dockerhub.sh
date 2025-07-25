#!/bin/bash

# Build and Push to Docker Hub Script
# Builds x86 images and pushes to Docker Hub (public registry)

set -e

# Configuration
DOCKER_USERNAME="lukabratzee"  # Your Docker Hub username
BACKEND_IMAGE="$DOCKER_USERNAME/video-game-catalogue-backend"
FRONTEND_IMAGE="$DOCKER_USERNAME/video-game-catalogue-frontend"
VERSION="${1:-latest}"

echo "🚀 Building and pushing to Docker Hub (x86)"
echo "============================================"
echo "Username: $DOCKER_USERNAME"
echo "Version: $VERSION"
echo ""

# Check if logged in to Docker Hub (try to test login)
echo "🔍 Checking Docker Hub login..."
if ! docker pull hello-world > /dev/null 2>&1; then
    echo "⚠️  Please login to Docker Hub first:"
    echo "docker login"
    exit 1
fi
echo "✅ Docker Hub access confirmed"

# Function to build and push an x86 image
build_and_push() {
    local context=$1
    local image_name=$2
    
    echo "🏗️ Building x86 $image_name:$VERSION..."
    
    # Copy modules for build context
    cp -r ./modules ./$context/modules
    
    # Build for x86 and push
    docker buildx build \
        --platform linux/amd64 \
        -f ./$context/Dockerfile \
        -t "$image_name:$VERSION" \
        -t "$image_name:latest" \
        --push \
        ./$context
    
    # Cleanup
    rm -rf ./$context/modules
    
    echo "✅ Successfully built and pushed $image_name"
    echo ""
}

# Build and push both images
build_and_push "backend" "$BACKEND_IMAGE"
build_and_push "frontend" "$FRONTEND_IMAGE"

echo "🎉 All images built and pushed to Docker Hub!"
echo ""
echo "📋 Image URLs:"
echo "   Backend:  $BACKEND_IMAGE:$VERSION"
echo "   Frontend: $FRONTEND_IMAGE:$VERSION"
echo ""
echo "🔧 These are public and can be used directly in docker-compose"
