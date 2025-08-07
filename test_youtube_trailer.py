#!/usr/bin/env python3
"""
Test script to add a sample game and fetch its YouTube trailer
"""

import requests
import time
import os
import sys

# Add the parent directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from backend.fetch_youtube_trailers import fetch_trailer_for_single_game

# Backend URL
BACKEND_URL = "http://localhost:5001"

def add_test_game():
    """Add a test game to the database"""
    test_game = {
        "title": "The Legend of Zelda: Breath of the Wild",
        "cover_image": "https://images.igdb.com/igdb/image/upload/t_cover_big/co1u8j.jpg",
        "description": "Step into a world of discovery, exploration, and adventure in The Legend of Zelda: Breath of the Wild.",
        "publisher": ["Nintendo"],
        "platforms": ["Nintendo Switch"],
        "genres": ["Adventure", "Action", "RPG"],
        "series": ["The Legend of Zelda"],
        "release_date": "2017-03-03",
        "average_price": 42.99
    }
    
    try:
        response = requests.post(f"{BACKEND_URL}/add_game", json=test_game)
        if response.status_code == 201:
            print("✅ Test game added successfully!")
            return True
        else:
            print(f"❌ Failed to add test game: {response.status_code}")
            print(response.text)
            return False
    except requests.RequestException as e:
        print(f"❌ Error adding test game: {e}")
        return False

def get_latest_game_id():
    """Get the ID of the most recently added game"""
    try:
        response = requests.get(f"{BACKEND_URL}/games")
        if response.status_code == 200:
            games = response.json()
            if games:
                # Find the highest ID that's not -1
                valid_games = [game for game in games if game['id'] != -1]
                if valid_games:
                    return max(valid_games, key=lambda x: x['id'])['id']
        return None
    except requests.RequestException as e:
        print(f"❌ Error getting games: {e}")
        return None

def main():
    print("YouTube Trailer Test Script")
    print("===========================")
    
    print("\n1. Adding test game...")
    if not add_test_game():
        print("Failed to add test game. Exiting.")
        return
    
    print("\n2. Getting latest game ID...")
    game_id = get_latest_game_id()
    if not game_id:
        print("Failed to get game ID. Exiting.")
        return
    
    print(f"Latest game ID: {game_id}")
    
    print("\n3. Fetching YouTube trailer...")
    success = fetch_trailer_for_single_game(game_id)
    
    if success:
        print("✅ Test completed successfully!")
        print(f"You can now check the game detail page for game ID {game_id} to see the embedded trailer.")
    else:
        print("❌ Failed to fetch trailer.")

if __name__ == "__main__":
    main()
