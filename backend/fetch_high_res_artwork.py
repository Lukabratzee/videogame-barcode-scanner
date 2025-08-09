#!/usr/bin/env python3
"""
High Resolution Artwork Fetcher for Video Game Catalogue

This script uses the SteamGridDB API (the same source used by Steam ROM Manager)
to fetch high-quality artwork for games in the collection. SteamGridDB provides
much higher resolution images than IGDB.

SteamGridDB provides several artwork types:
- Grid Images (600x900 tall covers, 460x215/920x430 banners)
- Hero Images (large banner-style backgrounds)
- Logo Images (transparent logo overlays)
- Icon Images (app-style icons)

Usage:
    python fetch_high_res_artwork.py [--bulk] [--game-id ID] [--api-key KEY]
"""

import os
import sys
import sqlite3
import requests
import time
import argparse
import json
import re
import logging
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to the path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

# Load .env variables
load_dotenv()

# SteamGridDB API configuration
STEAMGRIDDB_API_BASE = "https://www.steamgriddb.com/api/v2"
DEFAULT_API_KEY = None  # Users need to get their own key from https://www.steamgriddb.com/profile/preferences/api

# Database configuration - use same logic as app.py
database_path = os.getenv("DATABASE_PATH", "").strip()
if not database_path:
    # Fallback to default path
    database_path = "data/games.db"

# If the path is not absolute, then join with PROJECT_ROOT
if not os.path.isabs(database_path):
    database_path = os.path.join(PROJECT_ROOT, database_path)

DATABASE_PATH = database_path

# Artwork storage configuration
ARTWORK_DIR = os.path.join(PROJECT_ROOT, "data", "artwork")
GRID_DIR = os.path.join(ARTWORK_DIR, "grids")      # 600x900 tall covers
HERO_DIR = os.path.join(ARTWORK_DIR, "heroes")     # Large banners
LOGO_DIR = os.path.join(ARTWORK_DIR, "logos")      # Transparent logos
ICON_DIR = os.path.join(ARTWORK_DIR, "icons")      # App icons

class SteamGridDBClient:
    """Client for interacting with SteamGridDB API"""
    
    def __init__(self, api_key=None):
        if not api_key:
            # Try to load from environment or config
            api_key = os.getenv('STEAMGRIDDB_API_KEY')
            if not api_key:
                # Smart config path detection for Docker vs local
                if os.getenv('DOCKER_ENV') or os.path.exists('/.dockerenv'):
                    # In Docker, the config is mounted at /app/config
                    config_path = "/app/config/config.json"
                else:
                    # Local development - config is relative to project root
                    config_path = os.path.join(PROJECT_ROOT, "config", "config.json")
                
                if os.path.exists(config_path):
                    try:
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                            api_key = config.get('steamgriddb_api_key')
                    except Exception as e:
                        print(f"Warning: Could not load config from {config_path}: {e}")
                else:
                    print(f"Warning: Config file not found at {config_path}")
        
        if not api_key:
            raise ValueError(
                "SteamGridDB API key required. Get one from https://www.steamgriddb.com/profile/preferences/api\n"
                "Set it as environment variable STEAMGRIDDB_API_KEY or pass with --api-key"
            )
        
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'User-Agent': 'Video-Game-Catalogue/1.0'
        })
        
        # Create artwork directories
        for directory in [ARTWORK_DIR, GRID_DIR, HERO_DIR, LOGO_DIR, ICON_DIR]:
            os.makedirs(directory, exist_ok=True)
    
    def search_game(self, title):
        """Search for a game on SteamGridDB"""
        try:
            url = f"{STEAMGRIDDB_API_BASE}/search/autocomplete/{requests.utils.quote(title)}"
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            return data.get('data', [])
        except requests.exceptions.RequestException as e:
            print(f"Error searching for '{title}': {e}")
            return []
    
    def get_grids(self, game_id, dimensions=None, styles=None, nsfw=False, humor=False):
        """Get grid images (covers) for a game"""
        params = {
            'dimensions': dimensions or ['600x900'],  # Prefer tall covers
            'nsfw': 'any' if nsfw else 'false',
            'humor': 'any' if humor else 'false'
        }
        
        if styles:
            params['styles'] = styles
        
        try:
            url = f"{STEAMGRIDDB_API_BASE}/grids/game/{game_id}"
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get('data', [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching grids for game {game_id}: {e}")
            return []
    
    def get_heroes(self, game_id, styles=None, nsfw=False, humor=False):
        """Get hero images (banners) for a game"""
        params = {
            'nsfw': 'any' if nsfw else 'false',
            'humor': 'any' if humor else 'false'
        }
        
        if styles:
            params['styles'] = styles
        
        try:
            url = f"{STEAMGRIDDB_API_BASE}/heroes/game/{game_id}"
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get('data', [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching heroes for game {game_id}: {e}")
            return []
    
    def get_logos(self, game_id, styles=None, nsfw=False, humor=False):
        """Get logo images for a game"""
        params = {
            'nsfw': 'any' if nsfw else 'false',
            'humor': 'any' if humor else 'false'
        }
        
        if styles:
            params['styles'] = styles
        
        try:
            url = f"{STEAMGRIDDB_API_BASE}/logos/game/{game_id}"
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get('data', [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching logos for game {game_id}: {e}")
            return []
    
    def get_icons(self, game_id, styles=None, nsfw=False, humor=False):
        """Get icon images for a game"""
        params = {
            'nsfw': 'any' if nsfw else 'false',
            'humor': 'any' if humor else 'false'
        }
        
        if styles:
            params['styles'] = styles
        
        try:
            url = f"{STEAMGRIDDB_API_BASE}/icons/game/{game_id}"
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get('data', [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching icons for game {game_id}: {e}")
            return []
    
    def download_image(self, image_url, local_path):
        """Download an image from URL to local path"""
        try:
            response = self.session.get(image_url, stream=True)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True
        except Exception as e:
            print(f"Error downloading {image_url}: {e}")
            return False

class HighResArtworkFetcher:
    """Main class for fetching high resolution artwork"""
    
    def __init__(self, api_key=None):
        self.client = SteamGridDBClient(api_key)
        self.db_path = DATABASE_PATH
        
        # Ensure database exists
        # Validate database path
        if not os.path.exists(self.db_path):
            logging.error(f"Database not found at {self.db_path}")
            print(f"❌ Database not found at {self.db_path}")
            print(f"🔍 Current working directory: {os.getcwd()}")
            print(f"🔍 PROJECT_ROOT: {PROJECT_ROOT}")
            print(f"🔍 DATABASE_PATH env var: {os.getenv('DATABASE_PATH', 'Not set')}")
            raise FileNotFoundError(f"Database not found at {self.db_path}")
    
    def get_database_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def add_artwork_columns(self):
        """Deprecated: artwork columns are now created by migrations.
        Keeping this as a no-op for backward compatibility.
        """
        print("ℹ️  Skipping add_artwork_columns: handled by migrate_artwork_columns.py")
    
    def get_games_without_high_res_artwork(self, limit=None):
        """Get games that don't have high resolution artwork"""
        conn = self.get_database_connection()
        cursor = conn.cursor()
        
        # Get games without high-res cover URLs
        query = """
        SELECT id, title, platforms 
        FROM games 
        WHERE high_res_cover_url IS NULL OR high_res_cover_url = ''
        ORDER BY title
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        games = cursor.fetchall()
        conn.close()
        
        return games
    
    def search_and_fetch_artwork(self, game_id, title, platforms):
        """Search for a game and fetch all artwork types"""
        print(f"\n[{game_id}] Processing: {title} ({platforms})")
        
        # Create search query with title and first platform
        platform = platforms.split(',')[0].strip() if platforms else ""
        search_query = f"{title} {platform}".strip()
        
        # Search for the game
        search_results = self.client.search_game(search_query)
        
        if not search_results:
            print(f"❌ No results found for '{search_query}'")
            return False
        
        # Use the first (best) match
        game_data = search_results[0]
        steamgrid_id = game_data.get('id')
        game_name = game_data.get('name', 'Unknown')
        
        print(f"✅ Found: {game_name} (SteamGridDB ID: {steamgrid_id})")
        
        # Fetch all artwork types
        artwork_data = {}
        
        # 1. Grid Images (Covers) - prefer 600x900
        grids = self.client.get_grids(steamgrid_id, dimensions=['600x900'])
        if grids:
            best_grid = grids[0]  # First is usually best quality
            artwork_data['grid'] = {
                'url': best_grid['url'],
                'id': best_grid['id'],
                'author': best_grid.get('author', {}).get('name', 'Unknown')
            }
            print(f"  📸 Grid: {best_grid['url']}")
        
        # 2. Hero Images
        heroes = self.client.get_heroes(steamgrid_id)
        if heroes:
            best_hero = heroes[0]
            artwork_data['hero'] = {
                'url': best_hero['url'],
                'id': best_hero['id'],
                'author': best_hero.get('author', {}).get('name', 'Unknown')
            }
            print(f"  🎭 Hero: {best_hero['url']}")
        
        # 3. Logo Images
        logos = self.client.get_logos(steamgrid_id)
        if logos:
            best_logo = logos[0]
            artwork_data['logo'] = {
                'url': best_logo['url'],
                'id': best_logo['id'],
                'author': best_logo.get('author', {}).get('name', 'Unknown')
            }
            print(f"  🏷️  Logo: {best_logo['url']}")
        
        # 4. Icon Images
        icons = self.client.get_icons(steamgrid_id)
        if icons:
            best_icon = icons[0]
            artwork_data['icon'] = {
                'url': best_icon['url'],
                'id': best_icon['id'],
                'author': best_icon.get('author', {}).get('name', 'Unknown')
            }
            print(f"  🔲 Icon: {best_icon['url']}")
        
        if not artwork_data:
            print(f"❌ No artwork found for {game_name}")
            return False
        
        # Download and save artwork
        downloaded_paths = {}
        
        for artwork_type, data in artwork_data.items():
            url = data['url']
            artwork_id = data['id']
            
            # Determine file extension
            parsed_url = urlparse(url)
            file_ext = os.path.splitext(parsed_url.path)[1] or '.png'
            
            # Create filename with SteamGridDB ID for uniqueness
            filename = f"{game_id}_{artwork_type}_{artwork_id}{file_ext}"
            
            # Determine directory
            if artwork_type == 'grid':
                local_path = os.path.join(GRID_DIR, filename)
            elif artwork_type == 'hero':
                local_path = os.path.join(HERO_DIR, filename)
            elif artwork_type == 'logo':
                local_path = os.path.join(LOGO_DIR, filename)
            elif artwork_type == 'icon':
                local_path = os.path.join(ICON_DIR, filename)
            
            # Download the image
            if self.client.download_image(url, local_path):
                downloaded_paths[artwork_type] = {
                    'url': url,
                    'path': os.path.relpath(local_path, PROJECT_ROOT)
                }
                print(f"  ⬇️  Downloaded {artwork_type}: {filename}")
            else:
                print(f"  ❌ Failed to download {artwork_type}")
        
        # Update database
        if downloaded_paths:
            self.update_game_artwork(game_id, steamgrid_id, downloaded_paths)
            return True
        
        return False
    
    def update_game_artwork(self, game_id, steamgrid_id, artwork_paths):
        """Update game with high resolution artwork information"""
        conn = self.get_database_connection()
        cursor = conn.cursor()
        
        # Prepare update data
        update_data = {'steamgriddb_id': steamgrid_id}
        
        for artwork_type, data in artwork_paths.items():
            if artwork_type == 'grid':
                update_data['high_res_cover_url'] = data['url']
                update_data['high_res_cover_path'] = data['path']
            elif artwork_type == 'hero':
                update_data['hero_image_url'] = data['url']
                update_data['hero_image_path'] = data['path']
            elif artwork_type == 'logo':
                update_data['logo_image_url'] = data['url']
                update_data['logo_image_path'] = data['path']
            elif artwork_type == 'icon':
                update_data['icon_image_url'] = data['url']
                update_data['icon_image_path'] = data['path']
        
        # Build UPDATE query
        set_clauses = []
        values = []
        
        for column, value in update_data.items():
            set_clauses.append(f"{column} = ?")
            values.append(value)
        
        # Add timestamp
        set_clauses.append("artwork_last_updated = ?")
        values.append(datetime.now().isoformat())
        values.append(game_id)
        
        query = f"UPDATE games SET {', '.join(set_clauses)} WHERE id = ?"
        
        try:
            cursor.execute(query, values)
            conn.commit()
            print(f"  💾 Database updated for game ID {game_id}")
        except Exception as e:
            print(f"  ❌ Database error: {e}")
        finally:
            conn.close()
    
    def process_bulk_artwork(self, limit=None):
        """Process high resolution artwork for all games"""
        print("High Resolution Artwork Fetcher")
        print("=" * 50)
        print("Using SteamGridDB API (same source as Steam ROM Manager)")
        print("This will fetch high-quality covers, heroes, logos, and icons.\n")
        
        # Ensure artwork columns exist
        print("Checking database schema...")
        self.add_artwork_columns()
        
        # Get games without artwork
        games = self.get_games_without_high_res_artwork(limit)
        
        if not games:
            print("✅ All games already have high resolution artwork!")
            return
        
        print(f"\nFound {len(games)} games without high resolution artwork")
        
        if not limit:
            confirm = input(f"Process all {len(games)} games? This will take some time. (y/N): ")
            if confirm.lower() != 'y':
                print("Cancelled.")
                return
        
        print("\nStarting bulk artwork processing...")
        print("Rate limiting: 2 seconds between requests")
        
        success_count = 0
        error_count = 0
        
        for i, (game_id, title, platforms) in enumerate(games, 1):
            print(f"\n[{i}/{len(games)}] Processing...")
            
            try:
                if self.search_and_fetch_artwork(game_id, title, platforms):
                    success_count += 1
                else:
                    error_count += 1
                
                # Rate limiting
                if i < len(games):  # Don't wait after the last item
                    print("Waiting 2 seconds...")
                    time.sleep(2)
                    
            except KeyboardInterrupt:
                print(f"\n\n🛑 Process interrupted by user")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                error_count += 1
                continue
        
        print(f"\n" + "=" * 50)
        print(f"Bulk artwork processing complete!")
        print(f"✅ Success: {success_count}")
        print(f"❌ Errors: {error_count}")
        print(f"📁 Artwork saved to: {ARTWORK_DIR}")
    
    def process_single_game(self, game_id):
        """Process artwork for a single game"""
        conn = self.get_database_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, title, platforms FROM games WHERE id = ?", (game_id,))
        game = cursor.fetchone()
        conn.close()
        
        if not game:
            print(f"❌ Game with ID {game_id} not found")
            return False
        
        game_id, title, platforms = game
        
        print("High Resolution Artwork Fetcher")
        print("=" * 50)
        
        # Ensure artwork columns exist
        self.add_artwork_columns()
        
        return self.search_and_fetch_artwork(game_id, title, platforms)

def main():
    parser = argparse.ArgumentParser(description='Fetch high resolution artwork using SteamGridDB API')
    parser.add_argument('--bulk', action='store_true', help='Process all games without high-res artwork')
    parser.add_argument('--game-id', type=int, help='Process specific game by ID')
    parser.add_argument('--api-key', help='SteamGridDB API key (get from https://www.steamgriddb.com/profile/preferences/api)')
    parser.add_argument('--limit', type=int, help='Limit number of games to process (for testing)')
    
    args = parser.parse_args()
    
    if not args.bulk and not args.game_id:
        parser.error("Must specify either --bulk or --game-id")
    
    try:
        fetcher = HighResArtworkFetcher(api_key=args.api_key)
        
        if args.game_id:
            success = fetcher.process_single_game(args.game_id)
            sys.exit(0 if success else 1)
        elif args.bulk:
            fetcher.process_bulk_artwork(limit=args.limit)
        
    except KeyboardInterrupt:
        print(f"\n🛑 Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
