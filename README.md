## Video Game Catalogue

Self-hosted web app to catalogue your video game collection with a simple web UI. Add games from IGDB, track prices, view a gallery, attach high‑resolution artwork, and keep everything stored locally.

### Key features
- Add games via IGDB search (name or ID); optional barcode scan workflow
- Price tracking from eBay, Amazon, CeX, or PriceCharting with price history
- Gallery view with filters, tags, ratings, and completion status
- High‑resolution artwork from SteamGridDB; manual artwork upload supported
- YouTube trailer links stored and shown in game detail views
- CSV export of your collection

## Quick start

Prerequisites: Docker Desktop running.

- Mac/Linux:
```bash
./run-video-game-catalogue.sh
```

- Windows (PowerShell):
```powershell
./run-video-game-catalogue.ps1
```

The script will create required folders, pull images, generate the compose file, and start everything.

Open the app:
- Frontend: http://localhost:8501
- Backend health: http://localhost:5001/health

## Storage and data

The script sets up persistent volumes. Equivalent docker-compose mappings:

```yaml
services:
  backend:
    volumes:
      - ./data:/app/data     # SQLite DB and artwork live here
      - ./config:/app/config # App config persists here
  frontend:
    depends_on:
      - backend
```

Directory layout created on first run:

```yaml
data/
  games.db
  artwork/
    grids/
    heroes/
    logos/
    icons/
config/
  config.json
```

## Configuration

You do not need to set environment variables when using Docker. Configuration is read from `config/config.json` inside the mounted `config/` folder. The quick‑start scripts create this file for you if it doesn't exist.

Edit `config/config.json` and provide your own keys:

```json
{
  "price_source": "PriceCharting",
  "steamgriddb_api_key": "YOUR_STEAMGRIDDB_API_KEY", 
  "igdb_client_id": "YOUR_TWITCH_IGDB_CLIENT_ID",
  "igdb_client_secret": "YOUR_TWITCH_IGDB_CLIENT_SECRET"
}
```

- `price_source`: one of `eBay`, `Amazon`, `CeX`, `PriceCharting`.
- `steamgriddb_api_key`: optional, enables fetching high‑resolution artwork.
- `igdb_client_id` / `igdb_client_secret`: required for IGDB search.

The app persists your choices back into this file, so you can also change sources from the UI.

## Example docker-compose (Portainer/Compose)

```yaml
services:
  backend:
    image: lukabratzee/video-game-catalogue-backend:latest
    pull_policy: always
    platform: linux/amd64
    container_name: video-game-catalogue-backend-debug
    ports:
      - "5002:5001"   # Host 5002 → container 5001 (Flask listens on 5001)
    environment:
      - DATABASE_PATH=/app/data/games.db
      - BACKEND_PORT=5001   # Optional; app binds 0.0.0.0:5001
      - DOCKER_ENV=true
      - PYTHONUNBUFFERED=1
      - DEBUG=true
    volumes:
      - /root/docker/video-game-catalogue/data:/app/data:rw
      - /root/docker/video-game-catalogue/config:/app/config:rw
    # Simplified health check for debugging
    healthcheck:
      test: ["CMD-SHELL", "ps aux | grep app.py"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 30s
    restart: "no"  # Don't restart so we can see the logs

  frontend:
    image: lukabratzee/video-game-catalogue-frontend:latest
    pull_policy: always
    platform: linux/amd64
    container_name: video-game-catalogue-frontend-debug
    ports:
      - "8501:8501"
    environment:
      # Inside the Docker network, call the backend on its container port (5001)
      - BACKEND_HOST=backend
      - BACKEND_PORT=5001
      # What the user's browser can reach. If you expose backend as 5002 on your host:
      - BACKEND_BROWSER_BASE_URL=http://localhost:5002
      - FRONTEND_PORT=8501
    # Remove dependency for now to test backend separately
    # depends_on:
    #   backend:
    #     condition: service_healthy
    restart: "no"

volumes:
  data:
    driver: local
  config:
    driver: local

networks:
  default:
    driver: bridge
```

Notes:
- Internal vs browser ports:
  - Frontend container makes server-side HTTP calls to `http://backend:5001`.
  - The browser loads images from the host’s published port (e.g., `http://localhost:5002`).
  - `BACKEND_BROWSER_BASE_URL` controls the base used in image URLs that the browser fetches.
- If you access from another device, set `BACKEND_BROWSER_BASE_URL` to your host IP:
  - Example: `http://192.168.1.111:5002`

 

## Further reading

- High‑res artwork: `HIGH_RES_ARTWORK_GUIDE.md`
- YouTube trailers: `YOUTUBE_TRAILER_INTEGRATION.md`
- Gallery API notes: `GALLERY_PHASE1_DOCS.md`
- Price alerts: `PRICE_ALERTS_GUIDE.md`


