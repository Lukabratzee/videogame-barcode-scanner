#!/usr/bin/env python3
"""
Gallery Population Script for Existing Games

This script populates gallery metadata and tag associations for all existing games
in the database. It analyzes existing game data (genres, platforms) and creates
appropriate gallery entries with intelligent tag mappings.

Features:
- Creates gallery metadata for all existing games
- Maps genres to tags intelligently 
- Adds missing tags needed for existing game genres
- Sets reasonable defaults for completion status and other metadata
- Handles platform-specific tag assignments

Author: Video Game Catalogue Team  
Date: July 31, 2025
"""

import sqlite3
import os
import sys
from datetime import datetime
import re

# Use DATABASE_PATH environment variable if set, otherwise use data directory
if 'DATABASE_PATH' in os.environ:
    db_path = os.environ['DATABASE_PATH']
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, '..', 'data', 'games.db')

def add_missing_tags(cursor):
    """Add tags that are missing but needed for existing game genres"""
    
    print("🏷️  Adding missing tags for existing game genres...")
    
    # Additional tags needed based on the actual genres found in the database
    additional_tags = [
        ('Fighting', '#dc2626', 'Combat and martial arts games'),
        ('Visual Novel', '#a855f7', 'Story-driven interactive fiction games'),
        ('Music', '#f59e0b', 'Rhythm and music-based games'),
        ('Card & Board Game', '#6b7280', 'Digital card and board games'),
        ('Quiz/Trivia', '#10b981', 'Knowledge and trivia games'),
        ('Tactical', '#1e40af', 'Turn-based tactical combat games'),
        ('Beat em up', '#ef4444', 'Side-scrolling fighting games'),
        ('Arcade', '#f97316', 'Classic arcade-style games'),
        ('Point and Click', '#8b5cf6', 'Adventure games with point-and-click interface'),
        ('Horror', '#7f1d1d', 'Horror and suspense games'),
        ('Stealth', '#374151', 'Stealth and infiltration games'),
        ('Open World', '#059669', 'Large open-world exploration games'),
        ('Co-op', '#0891b2', 'Cooperative multiplayer games'),
        ('Retro Collection', '#7c3aed', 'Collections and remasters of classic games')
    ]
    
    added_count = 0
    for tag_name, color, description in additional_tags:
        try:
            cursor.execute('''
            INSERT OR IGNORE INTO game_tags (tag_name, tag_color, tag_description)
            VALUES (?, ?, ?)
            ''', (tag_name, color, description))
            
            if cursor.rowcount > 0:
                added_count += 1
                print(f"   ✅ Added tag: {tag_name}")
            
        except Exception as e:
            print(f"   ⚠️  Warning: Could not add tag {tag_name}: {e}")
    
    print(f"✅ Added {added_count} new tags")
    return added_count

def create_genre_tag_mapping():
    """Create intelligent mapping from game genres to gallery tags"""
    
    # Map database genres to gallery tags
    # Some genres map to multiple tags, some tags are inferred from context
    genre_to_tags = {
        # Direct mappings
        'Adventure': ['Adventure'],
        'Role-playing (RPG)': ['RPG'],
        'Shooter': ['Shooter', 'Action'],
        'Platform': ['Platformer'],
        'Puzzle': ['Puzzle'], 
        'Racing': ['Racing'],
        'Sport': ['Sports'],
        'Strategy': ['Strategy'],
        'Fighting': ['Fighting', 'Action'],
        'Simulator': ['Simulation'],
        'Music': ['Music'],
        'Arcade': ['Arcade', 'Retro'],
        'Indie': ['Indie'],
        'Visual Novel': ['Visual Novel'],
        'Card & Board Game': ['Card & Board Game'],
        'Quiz/Trivia': ['Quiz/Trivia'],
        
        # Complex mappings
        'Tactical': ['Tactical', 'Strategy'],
        'Turn-based strategy (TBS)': ['Tactical', 'Strategy'],
        'Real Time Strategy (RTS)': ['Strategy'],
        "Hack and slash/Beat 'em up": ['Beat em up', 'Action'],
        'Point-and-click': ['Point and Click', 'Adventure'],
        
        # Additional contextual mappings
        'Action': ['Action'],  # Catch-all action genre
    }
    
    return genre_to_tags

def create_platform_tag_mapping():
    """Create mapping from platforms to era/platform tags"""
    
    platform_to_tags = {
        # Retro consoles
        'Nintendo 64': ['Retro'],
        'PlayStation': ['Retro'], 
        'Game Boy': ['Retro'],
        'Game Boy Color': ['Retro'],
        'Game Boy Advance': ['Retro'],
        'Dreamcast': ['Retro'],
        'Sega Mega Drive/Genesis': ['Retro'],
        'Sega Saturn': ['Retro'],
        'Nintendo GameCube': ['Retro'],
        'PlayStation 2': ['Retro'],
        'Xbox': ['Retro'],
        
        # Modern platforms - no automatic retro tag
        'PlayStation 3': [],
        'PlayStation 4': [],
        'PlayStation 5': [],
        'PlayStation Portable': [],
        'PlayStation Vita': [],
        'PlayStation VR': [],
        'Xbox 360': [],
        'Xbox One': [],
        'Nintendo 3DS': [],
        'Nintendo Switch': [],
    }
    
    return platform_to_tags

def get_tags_for_game(game_data, genre_mapping, platform_mapping):
    """Analyze a game and return appropriate tags"""
    
    game_id, title, platforms, genres, publisher = game_data
    tags = set()
    
    # Process genres
    if genres:
        genre_list = [g.strip() for g in genres.split(',')]
        for genre in genre_list:
            if genre in genre_mapping:
                tags.update(genre_mapping[genre])
    
    # Process platforms for era-based tags
    if platforms:
        platform_list = [p.strip() for p in platforms.split(',')]
        for platform in platform_list:
            if platform in platform_mapping:
                tags.update(platform_mapping[platform])
    
    # Add contextual tags based on title analysis
    title_lower = title.lower()
    
    # Detect collections/remasters
    if any(keyword in title_lower for keyword in ['collection', 'anthology', 'trilogy', 'compilation', 'hd collection', 'remaster']):
        tags.add('Retro Collection')
    
    # Detect multiplayer indicators
    if any(keyword in title_lower for keyword in ['multiplayer', 'online', 'co-op', 'versus', 'tournament']):
        tags.add('Multiplayer')
    
    # Detect horror games
    if any(keyword in title_lower for keyword in ['horror', 'evil', 'dead', 'zombie', 'fear', 'nightmare', 'darkness', 'silent hill', 'resident evil']):
        tags.add('Horror')
    
    # Detect stealth games  
    if any(keyword in title_lower for keyword in ['stealth', 'assassin', 'thief', 'ninja', 'infiltrat', 'espionage']):
        tags.add('Stealth')
    
    # Detect open world games
    if any(keyword in title_lower for keyword in ['open world', 'gta', 'grand theft auto', 'red dead', 'elder scrolls', 'fallout', 'witcher']):
        tags.add('Open World')
    
    return list(tags)

def populate_gallery_metadata(cursor):
    """Create gallery metadata entries for all existing games"""
    
    print("📊 Creating gallery metadata for existing games...")
    
    # Get all existing games
    cursor.execute('''
    SELECT id, title, platforms, genres, publisher 
    FROM games 
    WHERE id != -1
    ORDER BY id
    ''')
    
    existing_games = cursor.fetchall()
    print(f"Found {len(existing_games)} games to process")
    
    created_count = 0
    for game_data in existing_games:
        game_id = game_data[0]
        
        try:
            # Create gallery metadata with sensible defaults
            cursor.execute('''
            INSERT OR IGNORE INTO game_gallery_metadata (
                game_id,
                display_priority,
                gallery_enabled,
                completion_status,
                favorite,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                game_id,
                0,  # Default priority
                1,  # Gallery enabled
                'not_started',  # Default completion status
                0,  # Not favorite by default
                datetime.now().isoformat()
            ))
            
            if cursor.rowcount > 0:
                created_count += 1
                
        except Exception as e:
            print(f"   ⚠️  Warning: Could not create gallery metadata for game {game_id}: {e}")
    
    print(f"✅ Created gallery metadata for {created_count} games")
    return created_count

def populate_tag_associations(cursor):
    """Create tag associations for all existing games"""
    
    print("🔗 Creating tag associations for existing games...")
    
    # Get tag mappings
    genre_mapping = create_genre_tag_mapping()
    platform_mapping = create_platform_tag_mapping()
    
    # Get all tag IDs for quick lookup
    cursor.execute('SELECT id, tag_name FROM game_tags')
    tag_name_to_id = {row[1]: row[0] for row in cursor.fetchall()}
    
    # Get all existing games
    cursor.execute('''
    SELECT id, title, platforms, genres, publisher 
    FROM games 
    WHERE id != -1
    ORDER BY id
    ''')
    
    existing_games = cursor.fetchall()
    
    total_associations = 0
    games_processed = 0
    
    for game_data in existing_games:
        game_id = game_data[0]
        title = game_data[1]
        
        # Get appropriate tags for this game
        suggested_tags = get_tags_for_game(game_data, genre_mapping, platform_mapping)
        
        game_associations = 0
        for tag_name in suggested_tags:
            if tag_name in tag_name_to_id:
                tag_id = tag_name_to_id[tag_name]
                
                try:
                    cursor.execute('''
                    INSERT OR IGNORE INTO game_tag_associations (game_id, tag_id, created_at)
                    VALUES (?, ?, ?)
                    ''', (game_id, tag_id, datetime.now().isoformat()))
                    
                    if cursor.rowcount > 0:
                        game_associations += 1
                        total_associations += 1
                        
                except Exception as e:
                    print(f"   ⚠️  Warning: Could not associate tag {tag_name} with game {game_id}: {e}")
        
        games_processed += 1
        if games_processed % 50 == 0:
            print(f"   Processed {games_processed}/{len(existing_games)} games...")
    
    print(f"✅ Created {total_associations} tag associations across {games_processed} games")
    return total_associations

def run_population():
    """Execute the gallery population for existing games"""
    
    print("🚀 Starting Gallery Population for Existing Games")
    print(f"📍 Database: {db_path}")
    
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Check if gallery tables exist
        cursor.execute('''
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name = 'game_gallery_metadata'
        ''')
        
        if not cursor.fetchone():
            print("❌ Gallery tables not found! Please run migrate_gallery_v1.py first.")
            return False
        
        # Check how many games already have gallery metadata
        cursor.execute('SELECT COUNT(*) FROM game_gallery_metadata')
        existing_metadata = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM games WHERE id != -1')
        total_games = cursor.fetchone()[0]
        
        print(f"📊 Found {total_games} games, {existing_metadata} already have gallery metadata")
        
        if existing_metadata == total_games:
            print("✅ All games already have gallery metadata!")
            return True
        
        # Step 1: Add missing tags
        added_tags = add_missing_tags(cursor)
        
        # Step 2: Create gallery metadata 
        created_metadata = populate_gallery_metadata(cursor)
        
        # Step 3: Create tag associations
        created_associations = populate_tag_associations(cursor)
        
        # Commit all changes
        conn.commit()
        
        print(f"\n🎉 Gallery population completed successfully!")
        print(f"📊 Summary:")
        print(f"   • Added {added_tags} new tags")
        print(f"   • Created gallery metadata for {created_metadata} games")
        print(f"   • Created {created_associations} tag associations")
        print(f"📅 Population timestamp: {datetime.now().isoformat()}")
        
        # Show some stats
        cursor.execute('SELECT COUNT(*) FROM game_tags')
        total_tags = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM game_gallery_metadata')
        total_metadata = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM game_tag_associations')
        total_associations = cursor.fetchone()[0]
        
        print(f"\n📈 Final counts:")
        print(f"   • Total tags: {total_tags}")
        print(f"   • Games with metadata: {total_metadata}")
        print(f"   • Total tag associations: {total_associations}")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error during population: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during population: {e}")
        return False

def show_sample_results():
    """Show sample results after population"""
    
    print("\n🔍 Sample results:")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Show games with the most tags
        cursor.execute('''
        SELECT g.title, COUNT(gta.tag_id) as tag_count,
               GROUP_CONCAT(gt.tag_name, ', ') as tags
        FROM games g
        JOIN game_tag_associations gta ON g.id = gta.game_id
        JOIN game_tags gt ON gta.tag_id = gt.id
        WHERE g.id != -1
        GROUP BY g.id, g.title
        ORDER BY tag_count DESC
        LIMIT 5
        ''')
        
        results = cursor.fetchall()
        print("🏆 Games with most tags:")
        for title, count, tags in results:
            print(f"   • {title} ({count} tags): {tags}")
        
        # Show tag distribution
        cursor.execute('''
        SELECT gt.tag_name, COUNT(gta.game_id) as game_count
        FROM game_tags gt
        LEFT JOIN game_tag_associations gta ON gt.id = gta.tag_id
        GROUP BY gt.id, gt.tag_name
        ORDER BY game_count DESC
        LIMIT 10
        ''')
        
        results = cursor.fetchall()
        print(f"\n📊 Most popular tags:")
        for tag_name, count in results:
            print(f"   • {tag_name}: {count} games")
        
        conn.close()
        
    except Exception as e:
        print(f"⚠️  Could not show sample results: {e}")

if __name__ == "__main__":
    success = run_population()
    if success:
        show_sample_results()
    else:
        sys.exit(1)
