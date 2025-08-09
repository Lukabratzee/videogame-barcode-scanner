#!/usr/bin/env python3
"""
Gallery Feature Database Migration - Version 1.0.0

This migration adds the necessary tables for the Gallery feature:
1. game_gallery_metadata - Extended metadata for gallery display
2. game_tags - Custom tagging system for filtering
3. game_tag_associations - Many-to-many relationship between games and tags
4. gallery_settings - Global gallery configuration settings

Author: Video Game Catalogue Team
Date: July 31, 2025
"""

import sqlite3
import os
import sys
from datetime import datetime

def _resolve_db_path() -> str:
    """Resolve DB path at runtime to avoid stale environment between tests."""
    if 'DATABASE_PATH' in os.environ and os.environ['DATABASE_PATH'].strip():
        path = os.environ['DATABASE_PATH'].strip()
        if not os.path.isabs(path):
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            path = os.path.join(base, path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, 'games.db')

def run_migration():
    """Execute the gallery feature database migration"""
    
    print("🚀 Starting Gallery Feature Migration v1.0.0")
    db_path = _resolve_db_path()
    print(f"📍 Database: {db_path}")
    
    if not os.path.exists(db_path):
        print("❌ Database file not found! Please run database_setup.py first.")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")
        
        print("\n📋 Creating gallery metadata table...")
        
        # 1. Create game_gallery_metadata table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_gallery_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            trailer_url TEXT,
            gamefaqs_url TEXT,
            powerpyx_url TEXT,
            metacritic_url TEXT,
            steam_url TEXT,
            psn_url TEXT,
            xbox_url TEXT,
            nintendo_url TEXT,
            display_priority INTEGER DEFAULT 0,
            gallery_enabled BOOLEAN DEFAULT 1,
            completion_status TEXT DEFAULT 'not_started' CHECK (completion_status IN ('not_started', 'in_progress', 'completed', 'abandoned')),
            personal_rating INTEGER CHECK (personal_rating >= 1 AND personal_rating <= 10),
            play_time_hours REAL,
            date_acquired TEXT,
            date_started TEXT,
            date_completed TEXT,
            notes TEXT,
            favorite BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games (id) ON DELETE CASCADE,
            UNIQUE (game_id)
        )
        ''')
        
        print("✅ Created game_gallery_metadata table")
        
        print("\n🏷️  Creating tags system...")
        
        # 2. Create game_tags table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_name TEXT NOT NULL UNIQUE,
            tag_color TEXT DEFAULT '#6366f1',
            tag_description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            display_order INTEGER DEFAULT 0
        )
        ''')
        
        print("✅ Created game_tags table")
        
        # 3. Create game_tag_associations table (many-to-many)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_tag_associations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games (id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES game_tags (id) ON DELETE CASCADE,
            UNIQUE (game_id, tag_id)
        )
        ''')
        
        print("✅ Created game_tag_associations table")
        
        print("\n⚙️  Creating gallery settings...")
        
        # 4. Create gallery_settings table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS gallery_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT NOT NULL UNIQUE,
            setting_value TEXT,
            setting_type TEXT DEFAULT 'string' CHECK (setting_type IN ('string', 'integer', 'boolean', 'json')),
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        print("✅ Created gallery_settings table")
        
        print("\n🌱 Seeding default data...")
        
        # Insert default tags
        default_tags = [
            ('Action', '#ef4444', 'High-energy games with combat and excitement'),
            ('Adventure', '#10b981', 'Story-driven exploration games'),
            ('RPG', '#8b5cf6', 'Role-playing games with character progression'),
            ('Puzzle', '#f59e0b', 'Brain-teasing and logic games'),
            ('Strategy', '#3b82f6', 'Strategic thinking and planning games'),
            ('Sports', '#84cc16', 'Athletic and sports simulation games'),
            ('Racing', '#f97316', 'High-speed racing and driving games'),
            ('Simulation', '#06b6d4', 'Real-world simulation games'),
            ('Platformer', '#ec4899', 'Jump and run platform games'),
            ('Shooter', '#dc2626', 'Shooting and combat games'),
            ('Indie', '#6366f1', 'Independent developer games'),
            ('Retro', '#7c3aed', 'Classic and vintage games'),
            ('Multiplayer', '#059669', 'Games with multiplayer features'),
            ('Completed', '#22c55e', 'Games that have been finished'),
            ('In Progress', '#eab308', 'Currently playing'),
            ('Wishlist', '#64748b', 'Games to acquire'),
            ('Favorite', '#e11d48', 'Personal favorite games')
        ]
        
        for tag_name, color, description in default_tags:
            cursor.execute('''
            INSERT OR IGNORE INTO game_tags (tag_name, tag_color, tag_description)
            VALUES (?, ?, ?)
            ''', (tag_name, color, description))
        
        print("✅ Seeded default tags")
        
        # Insert default gallery settings
        default_settings = [
            ('gallery_tiles_per_row', '6', 'integer', 'Number of game tiles per row in gallery view'),
            ('gallery_view_mode', '3d', 'string', 'Gallery view mode: 2d, 3d, or grid'),
            ('gallery_sort_default', 'title_asc', 'string', 'Default sort order for gallery'),
            ('gallery_enable_animations', 'true', 'boolean', 'Enable 3D animations and transitions'),
            ('gallery_show_completion_badges', 'true', 'boolean', 'Show completion status badges on tiles'),
            ('gallery_show_rating_stars', 'true', 'boolean', 'Show personal rating stars on tiles'),
            ('gallery_autoplay_trailers', 'false', 'boolean', 'Autoplay trailers in game detail view'),
            ('gallery_theme_color', '#6366f1', 'string', 'Primary theme color for gallery interface')
        ]
        
        for key, value, type_val, description in default_settings:
            cursor.execute('''
            INSERT OR IGNORE INTO gallery_settings (setting_key, setting_value, setting_type, description)
            VALUES (?, ?, ?, ?)
            ''', (key, value, type_val, description))
        
        print("✅ Seeded default gallery settings")
        
        print("\n🔗 Creating indexes for performance...")
        
        # Create indexes for better query performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_gallery_metadata_game_id ON game_gallery_metadata(game_id)",
            "CREATE INDEX IF NOT EXISTS idx_gallery_metadata_completion ON game_gallery_metadata(completion_status)",
            "CREATE INDEX IF NOT EXISTS idx_gallery_metadata_rating ON game_gallery_metadata(personal_rating)",
            "CREATE INDEX IF NOT EXISTS idx_gallery_metadata_favorite ON game_gallery_metadata(favorite)",
            "CREATE INDEX IF NOT EXISTS idx_tag_associations_game_id ON game_tag_associations(game_id)",
            "CREATE INDEX IF NOT EXISTS idx_tag_associations_tag_id ON game_tag_associations(tag_id)",
            "CREATE INDEX IF NOT EXISTS idx_gallery_settings_key ON gallery_settings(setting_key)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        print("✅ Created performance indexes")
        
        # Create triggers for updating timestamps
        print("\n⏰ Creating update timestamp triggers...")
        
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_gallery_metadata_timestamp 
        AFTER UPDATE ON game_gallery_metadata
        BEGIN
            UPDATE game_gallery_metadata 
            SET updated_at = CURRENT_TIMESTAMP 
            WHERE id = NEW.id;
        END
        ''')
        
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_gallery_settings_timestamp 
        AFTER UPDATE ON gallery_settings
        BEGIN
            UPDATE gallery_settings 
            SET updated_at = CURRENT_TIMESTAMP 
            WHERE id = NEW.id;
        END
        ''')
        
        print("✅ Created timestamp triggers")
        
        # Commit all changes
        conn.commit()
        
        print("\n📊 Verifying migration...")
        
        # Verify tables were created (restrict to tables only)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE '%gallery%' OR name LIKE '%tag%')")
        new_tables = cursor.fetchall()
        
        print(f"✅ Created {len(new_tables)} new tables:")
        for table in new_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"   • {table[0]} ({count} rows)")
        
        conn.close()
        
        print(f"\n🎉 Gallery Feature Migration completed successfully!")
        print(f"📅 Migration timestamp: {datetime.now().isoformat()}")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error during migration: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during migration: {e}")
        return False

def rollback_migration():
    """Rollback the gallery feature migration"""
    
    print("🔄 Rolling back Gallery Feature Migration...")
    
    try:
        db_path = _resolve_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Drop tables in reverse order (respect foreign keys)
        tables_to_drop = [
            'game_tag_associations',
            'game_tags', 
            'game_gallery_metadata',
            'gallery_settings'
        ]
        
        for table in tables_to_drop:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            print(f"✅ Dropped table: {table}")
        
        conn.commit()
        conn.close()
        
        print("🎉 Rollback completed successfully!")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error during rollback: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback_migration()
    else:
        run_migration()
