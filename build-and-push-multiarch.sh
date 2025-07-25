#!/bin/bash

# Build and Push Multi-Architecture Images to Docker Hub
# Builds for both linux/amd64 and linux/arm64

set -e

# Configuration
DOCKER_USERNAME="lukabratzee"
BACKEND_IMAGE="$DOCKER_USERNAME/video-game-catalogue-backend"
FRONTEND_IMAGE="$DOCKER_USERNAME/video-game-catalogue-frontend"
VERSION="${1:-latest}"

echo "🚀 Building TRUE multi-architecture images for Docker Hub"
echo "=========================================================="
echo "Username: $DOCKER_USERNAME" 
echo "Version: $VERSION"
echo "Platforms: linux/amd64,linux/arm64"
echo ""

# Check if logged in to Docker Hub
echo "🔍 Checking Docker Hub login..."
if ! docker pull hello-world > /dev/null 2>&1; then
    echo "⚠️  Please login to Docker Hub first:"
    echo "docker login"
    exit 1
fi
echo "✅ Docker Hub access confirmed"

# Create buildx builder if it doesn't exist
echo "🔧 Setting up multi-arch builder..."
docker buildx create --name multiarch-builder --use 2>/dev/null || docker buildx use multiarch-builder
docker buildx inspect --bootstrap

# Function to build and push multi-arch image
build_and_push_multiarch() {
    local context=$1
    local image_name=$2
    
    echo "🏗️ Building multi-arch $image_name:$VERSION..."
    
    # Copy modules for build context
    cp -r ./modules ./$context/modules
    
    # Build for multiple architectures and push from context directory
    # This allows the Dockerfile COPY commands to work correctly
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        -f ./$context/Dockerfile \
        -t "$image_name:$VERSION" \
        -t "$image_name:latest" \
        --push \
        ./$context
    
    # Cleanup
    rm -rf ./$context/modules
    
    echo "✅ Multi-arch build complete for $image_name"
}

# Build backend
echo ""
echo "🔨 Building backend (multi-arch)..."
build_and_push_multiarch "backend" "$BACKEND_IMAGE"

# Build frontend  
echo ""
echo "🔨 Building frontend (multi-arch)..."
build_and_push_multiarch "frontend" "$FRONTEND_IMAGE"

echo ""
echo "🎉 Successfully built and pushed multi-architecture images!"
echo ""
echo "📋 Images available:"
echo "   Backend:  $BACKEND_IMAGE:$VERSION"
echo "   Frontend: $FRONTEND_IMAGE:$VERSION"
echo ""
echo "🏗️ Architectures: linux/amd64, linux/arm64"
echo "📍 Registry: Docker Hub (public)"
echo ""
echo "🔍 Verify multi-arch support:"
echo "   docker manifest inspect $BACKEND_IMAGE:$VERSION"
echo "   docker manifest inspect $FRONTEND_IMAGE:$VERSION"
