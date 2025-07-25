# X86 Deployment Guide

## Overview
This guide helps you deploy the Video Game Catalogue on x86 architecture using Docker Compose and GitHub Container Registry images.

## Prerequisites
- x86/AMD64 Linux VM or server
- Docker and Docker Compose installed
- Internet connection to pull images from GitHub Container Registry

## Quick Deployment

### 1. Create deployment directory
```bash
mkdir video-game-catalogue-deploy && cd video-game-catalogue-deploy
```

### 2. Download docker-compose file
```bash
curl -O https://raw.githubusercontent.com/lukabratzee/video-game-catalogue/multi-arch-support/docker-compose-ghcr.yml
```

### 3. Start the application
```bash
docker-compose -f docker-compose-ghcr.yml up -d
```

### 4. Access the application
- **Frontend**: http://your-vm-ip:8501
- **Backend API**: http://your-vm-ip:5001
- **Health Check**: http://your-vm-ip:5001/health

## Images Used
- Backend: `ghcr.io/lukabratzee/video-game-catalogue-backend:latest`
- Frontend: `ghcr.io/lukabratzee/video-game-catalogue-frontend:latest`

Both images are built for **linux/amd64** architecture and will work on x86 systems.

## Data Persistence
- Database: `./data/games.db`
- Config: `./config/`

## Troubleshooting

### Check image architecture
```bash
docker image inspect ghcr.io/lukabratzee/video-game-catalogue-backend:latest | grep Architecture
```

### View logs
```bash
docker-compose -f docker-compose-ghcr.yml logs
```

### Stop services
```bash
docker-compose -f docker-compose-ghcr.yml down
```

## Architecture Verification
The images are specifically built for x86 (linux/amd64) architecture. Docker will automatically pull the correct architecture when you run on an x86 system.
