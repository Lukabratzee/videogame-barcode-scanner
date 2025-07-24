#!/bin/bash

echo "🧹 Cleaning up Docker environment..."
docker-compose down --remove-orphans

echo "🏗️ Building containers with no cache..."
docker-compose build --no-cache

echo "🚀 Starting containers..."
docker-compose up -d

echo "⏱️ Waiting for services to start..."
sleep 10

echo "🔍 Checking container status..."
docker-compose ps

echo "📋 Backend logs:"
docker-compose logs backend --tail=20

echo "📋 Frontend logs:"
docker-compose logs frontend --tail=20

echo "🌐 Testing backend connectivity..."
curl -f http://localhost:5001/consoles || echo "❌ Backend not responding"

echo "🌐 Testing frontend connectivity..."
curl -f http://localhost:8501 || echo "❌ Frontend not responding"

echo "✅ Setup complete! You can access:"
echo "   Frontend: http://localhost:8501"
echo "   Backend API: http://localhost:5001"
