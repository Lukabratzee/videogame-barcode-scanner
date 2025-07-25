#!/bin/bash

# Test Multi-Architecture Docker Images
# This script tests if our images work on both AMD64 and ARM64

set -e

REGISTRY="ghcr.io"
USERNAME="lukabratzee"
BACKEND_IMAGE="$REGISTRY/$USERNAME/video-game-catalogue-backend:latest"
FRONTEND_IMAGE="$REGISTRY/$USERNAME/video-game-catalogue-frontend:latest"

echo "🧪 Testing Multi-Architecture Docker Images"
echo "==========================================="

# Function to inspect image architecture
inspect_image() {
    local image=$1
    echo "🔍 Inspecting $image..."
    
    # Check if image exists and get platform info
    if docker manifest inspect "$image" >/dev/null 2>&1; then
        echo "✅ Image exists in registry"
        echo "📋 Available platforms:"
        docker manifest inspect "$image" | jq -r '.manifests[] | "  - \(.platform.os)/\(.platform.architecture)"'
    else
        echo "❌ Image not found in registry"
        return 1
    fi
    echo ""
}

# Function to test running image on current platform
test_image() {
    local image=$1
    local name=$2
    
    echo "🚀 Testing $name on current platform..."
    
    # Try to pull and run basic command
    if docker run --rm --platform=linux/$(docker version --format '{{.Server.Arch}}') "$image" python --version; then
        echo "✅ $name runs successfully on current platform"
    else
        echo "❌ $name failed to run on current platform"
        return 1
    fi
    echo ""
}

# Main tests
echo "Testing backend image..."
inspect_image "$BACKEND_IMAGE"
test_image "$BACKEND_IMAGE" "Backend"

echo "Testing frontend image..."
inspect_image "$FRONTEND_IMAGE"
test_image "$FRONTEND_IMAGE" "Frontend"

echo "🎉 Multi-architecture testing complete!"
echo ""
echo "💡 To deploy on x86 Portainer:"
echo "   1. Push this branch to GitHub"
echo "   2. GitHub Actions will build multi-arch images automatically"
echo "   3. Use docker-compose-ghcr.yml on your Portainer host"
echo "   4. Docker will automatically pull the correct architecture"
