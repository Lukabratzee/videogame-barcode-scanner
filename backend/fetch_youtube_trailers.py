#!/usr/bin/env python3
"""
YouTube Trailer Fetcher
Automatically fetches and stores YouTube trailer URLs for games in the database
"""

import requests
import sqlite3
import os
import sys
import time
import re
from urllib.parse import quote, parse_qs, urlparse

# Add the parent directory to the path so we can import modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

def get_youtube_video_id(search_query):
    """
    Search YouTube and get the first video ID from results
    Uses YouTube's search results page scraping (simple approach)
    """
    try:
        # Format search query
        query = f"{search_query} trailer".replace(" ", "+")
        
        # YouTube search URL
        search_url = f"https://www.youtube.com/results?search_query={query}"
        
        # Headers to appear more like a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Get the search results page
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Look for video IDs in the HTML
        # YouTube video IDs are 11 characters long and appear in specific patterns
        video_id_pattern = r'"videoId":"([a-zA-Z0-9_-]{11})"'
        matches = re.findall(video_id_pattern, response.text)
        
        if matches:
            # Return the first video ID found
            return matches[0]
        
        # Alternative pattern
        video_id_pattern2 = r'/watch\?v=([a-zA-Z0-9_-]{11})'
        matches2 = re.findall(video_id_pattern2, response.text)
        
        if matches2:
            return matches2[0]
        
        print(f"No video ID found for search: {search_query}")
        return None
        
    except requests.RequestException as e:
        print(f"Error searching YouTube for '{search_query}': {e}")
        return None
    except Exception as e:
        print(f"Unexpected error searching for '{search_query}': {e}")
        return None

def get_games_without_trailers():
    """Get all games that don't have YouTube trailer URLs"""
    db_path = os.path.join(parent_dir, "data", "games.db")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get games without trailer URLs
        cursor.execute("""
            SELECT id, title, platforms 
            FROM games 
            WHERE youtube_trailer_url IS NULL OR youtube_trailer_url = ''
            ORDER BY id
        """)
        
        games = cursor.fetchall()
        conn.close()
        
        return games
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []

def update_game_trailer(game_id, youtube_url):
    """Update a game's YouTube trailer URL in the database"""
    db_path = os.path.join(parent_dir, "data", "games.db")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE games 
            SET youtube_trailer_url = ? 
            WHERE id = ?
        """, (youtube_url, game_id))
        
        conn.commit()
        conn.close()
        
        return True
        
    except sqlite3.Error as e:
        print(f"Database error updating game {game_id}: {e}")
        return False

def fetch_trailers_for_games(limit=None, delay=2):
    """
    Fetch YouTube trailers for games that don't have them
    
    Args:
        limit (int): Maximum number of games to process (None for all)
        delay (int): Delay between requests in seconds
    """
    print("Fetching games without trailers...")
    games = get_games_without_trailers()
    
    if not games:
        print("All games already have trailer URLs!")
        return
    
    total_games = len(games)
    if limit:
        games = games[:limit]
        print(f"Processing {len(games)} of {total_games} games (limited)")
    else:
        print(f"Processing all {total_games} games")
    
    successful = 0
    failed = 0
    
    for i, (game_id, title, platforms) in enumerate(games, 1):
        # Extract first platform from platforms field
        platform = ""
        if platforms:
            try:
                # Try to parse as JSON first
                import json
                platforms_list = json.loads(platforms)
                if isinstance(platforms_list, list) and platforms_list:
                    platform = platforms_list[0]
                elif isinstance(platforms_list, str):
                    platform = platforms_list
            except (json.JSONDecodeError, TypeError):
                # Fallback to treating as comma-separated string
                platform = platforms.split(',')[0].strip() if ',' in platforms else platforms
        
        print(f"\n[{i}/{len(games)}] Processing: {title} ({platform})")
        
        # Create search query
        search_query = f"{title} {platform}"
        
        # Get YouTube video ID
        video_id = get_youtube_video_id(search_query)
        
        if video_id:
            # Create full YouTube URL
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Update database
            if update_game_trailer(game_id, youtube_url):
                print(f"✅ Updated: {youtube_url}")
                successful += 1
            else:
                print(f"❌ Failed to update database for game {game_id}")
                failed += 1
        else:
            print(f"❌ No trailer found")
            failed += 1
        
        # Rate limiting - be nice to YouTube
        if i < len(games):  # Don't delay after the last item
            print(f"Waiting {delay} seconds...")
            time.sleep(delay)
    
    print(f"\n=== Summary ===")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total processed: {successful + failed}")

def fetch_trailer_for_single_game(game_id):
    """Fetch trailer for a specific game by ID"""
    db_path = os.path.join(parent_dir, "data", "games.db")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get game details
        cursor.execute("""
            SELECT id, title, platforms 
            FROM games 
            WHERE id = ?
        """, (game_id,))
        
        game = cursor.fetchone()
        conn.close()
        
        if not game:
            print(f"Game with ID {game_id} not found")
            return False
        
        game_id, title, platforms = game
        
        # Extract first platform
        platform = ""
        if platforms:
            try:
                import json
                platforms_list = json.loads(platforms)
                if isinstance(platforms_list, list) and platforms_list:
                    platform = platforms_list[0]
                elif isinstance(platforms_list, str):
                    platform = platforms_list
            except (json.JSONDecodeError, TypeError):
                platform = platforms.split(',')[0].strip() if ',' in platforms else platforms
        
        print(f"Fetching trailer for: {title} ({platform})")
        
        # Create search query
        search_query = f"{title} {platform}"
        
        # Get YouTube video ID
        video_id = get_youtube_video_id(search_query)
        
        if video_id:
            # Create full YouTube URL
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Update database
            if update_game_trailer(game_id, youtube_url):
                print(f"✅ Updated: {youtube_url}")
                return True
            else:
                print(f"❌ Failed to update database")
                return False
        else:
            print(f"❌ No trailer found")
            return False
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False

if __name__ == "__main__":
    print("YouTube Trailer Fetcher")
    print("======================")
    
    if len(sys.argv) > 1:
        try:
            game_id = int(sys.argv[1])
            print(f"Fetching trailer for game ID: {game_id}")
            fetch_trailer_for_single_game(game_id)
        except ValueError:
            print("Invalid game ID. Please provide a numeric game ID.")
            sys.exit(1)
    else:
        print("Fetching trailers for all games without them...")
        print("This will take some time due to rate limiting.")
        
        # Ask for confirmation
        response = input("\nContinue? (y/N): ").strip().lower()
        if response == 'y':
            fetch_trailers_for_games(delay=2)  # 2 second delay between requests
        else:
            print("Cancelled.")
