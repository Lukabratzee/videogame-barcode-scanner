#!/bin/bash

echo "🐳 Stopping and removing existing containers..."
docker-compose down

echo "🧹 Cleaning up Docker resources (optional - comment out if you want to keep images)..."
# Uncomment the next line if you want to clean up all Docker resources
# docker system prune -af

echo "🔨 Building Docker images without cache..."
docker-compose build --no-cache

echo "🚀 Starting containers in detached mode..."
docker-compose up -d

echo "📋 Container status:"
docker-compose ps

echo "📝 To view logs:"
echo "  Backend logs:  docker logs videogamescanner-backend -f"
echo "  Frontend logs: docker logs videogamescanner-frontend -f"
echo "  All logs:      docker-compose logs -f"

echo "🌐 Services should be available at:"
echo "  Frontend: http://localhost:8501"
echo "  Backend:  http://localhost:5001"

echo "✅ Docker setup complete!" 