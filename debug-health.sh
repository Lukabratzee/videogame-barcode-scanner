#!/bin/bash

echo "🔍 Testing backend health endpoint..."

# Wait for container to start
sleep 10

# Test the health endpoint and show detailed response
echo "📡 Checking health endpoint..."
curl -v http://localhost:5002/health

echo ""
echo "📋 Container logs:"
docker logs video-game-catalogue-backend-debug 2>&1 | tail -20

echo ""
echo "🔍 Container status:"
docker ps | grep video-game

echo ""
echo "🌐 Network connectivity test:"
docker exec video-game-catalogue-backend-debug curl -v http://localhost:5001/health 2>&1 || echo "Internal health check failed"
