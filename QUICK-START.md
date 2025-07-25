# 🎮 Video Game Catalogue - Easy Setup

**A self-contained Docker application for cataloging and managing your video game collection.**

## 🚀 One-Click Setup

### For Mac/Linux users:
```bash
curl -O https://raw.githubusercontent.com/your-repo/run-video-game-catalogue.sh
chmod +x run-video-game-catalogue.sh
./run-video-game-catalogue.sh
```

### For Windows users:
```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/your-repo/run-video-game-catalogue.ps1" -OutFile "run-video-game-catalogue.ps1"
.\run-video-game-catalogue.ps1
```

## 📋 Requirements

- **Docker Desktop** installed and running
- **5GB** free disk space
- **Ports 5001 and 8501** available

## ✨ What you get

- 🌐 **Web interface** at http://localhost:8501
- 🔍 **Game search** and cataloging
- 💰 **Price tracking** from eBay
- 📊 **Collection statistics**
- 🏷️ **Genre and platform filtering**
- 💾 **Automatic data persistence**

## 🛠️ Features

- ✅ **Multi-platform**: Works on Windows, Mac, Linux
- ✅ **Zero configuration**: Everything is included
- ✅ **Automatic updates**: Always pulls latest version
- ✅ **Secure**: Runs in isolated containers
- ✅ **Persistent data**: Your collection survives restarts

## 🎯 Perfect for

- Game collectors who want to track their collection
- Retro gaming enthusiasts
- Anyone wanting to organize their gaming library
- Price tracking for buying/selling decisions

## 🔧 Advanced Usage

- **View logs**: `docker-compose -f docker-compose-standalone.yml logs`
- **Stop application**: Press Ctrl+C or use the -Stop parameter (PowerShell)
- **Update to latest**: Just run the script again
- **Reset data**: Delete the `data/` folder before running

---

*The application includes web scraping capabilities for game information and price tracking. Multi-architecture Docker images ensure compatibility across different processors (Intel, AMD, Apple Silicon).*
