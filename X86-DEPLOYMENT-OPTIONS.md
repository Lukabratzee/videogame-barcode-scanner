# Local x86 Deployment Guide

## Option 1: Use Public Docker Hub Images

### Prerequisites
- Docker and Docker Compose on your x86 machine
- Internet connection

### Steps
1. Download the compose file:
```bash
curl -O https://your-gitea-server/path/docker-compose-dockerhub.yml
# OR copy the file manually
```

2. Start the application:
```bash
docker-compose -f docker-compose-dockerhub.yml up -d
```

## Option 2: Build Locally on x86 Machine

### Prerequisites
- Docker and Docker Compose
- Git access to your Gitea repository

### Steps
1. Clone the repository:
```bash
git clone http://your-gitea-server/lukabratzee/video-game-catalogue
cd video-game-catalogue
git checkout multi-arch-support
```

2. Build and run locally:
```bash
# This will build x86 images natively on the x86 machine
docker-compose up --build
```

## Which Option to Choose?

**Option 1 (Docker Hub)**: 
- ✅ No source code needed on target machine
- ✅ Faster deployment (no build time)
- ✅ Public images, no authentication needed
- ❌ Requires pushing to public registry

**Option 2 (Local Build)**:
- ✅ No public registry needed
- ✅ Full control over build process
- ❌ Requires source code on target machine
- ❌ Longer deployment time (build required)

## Access
- Frontend: http://your-x86-machine-ip:8501
- Backend: http://your-x86-machine-ip:5001/health
