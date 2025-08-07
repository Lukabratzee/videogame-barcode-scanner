#!/usr/bin/env python3
"""
Add price history table and functionality to track game prices over time.
This will allow us to show a chart of price changes for each game.
"""

import sqlite3
import os
from datetime import datetime

# Database path
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "games.db")

def create_price_history_table():
    """Create the price_history table to track game prices over time"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Create price_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                price REAL,
                price_source TEXT NOT NULL,
                date_recorded TEXT NOT NULL,
                currency TEXT DEFAULT 'GBP',
                FOREIGN KEY (game_id) REFERENCES games (id) ON DELETE CASCADE
            )
        """)
        
        print("✅ Created price_history table")
        
        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_history_game_id 
            ON price_history (game_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_history_date 
            ON price_history (date_recorded)
        """)
        
        print("✅ Created indexes for price_history table")
        
        conn.commit()
        
        # Check if the table was created successfully
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='price_history'")
        if cursor.fetchone()[0] > 0:
            print("✅ price_history table created successfully!")
            
            # Show the schema
            cursor.execute("PRAGMA table_info(price_history)")
            columns = cursor.fetchall()
            print("\n📋 Price History Table Schema:")
            for col in columns:
                print(f"  {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'}")
        
    except Exception as e:
        print(f"❌ Error creating price_history table: {e}")
        conn.rollback()
    finally:
        conn.close()

def migrate_existing_prices():
    """Migrate existing average_price data to price_history table"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Get all games with existing prices
        cursor.execute("""
            SELECT id, title, average_price 
            FROM games 
            WHERE average_price IS NOT NULL AND average_price > 0
        """)
        
        games_with_prices = cursor.fetchall()
        print(f"\n📊 Found {len(games_with_prices)} games with existing prices")
        
        # Get current timestamp
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Migrate existing prices to price_history
        migrated_count = 0
        for game_id, title, price in games_with_prices:
            # Check if this game already has price history
            cursor.execute("""
                SELECT COUNT(*) FROM price_history WHERE game_id = ?
            """, (game_id,))
            
            if cursor.fetchone()[0] == 0:  # No existing price history
                cursor.execute("""
                    INSERT INTO price_history (game_id, price, price_source, date_recorded)
                    VALUES (?, ?, ?, ?)
                """, (game_id, price, 'Migration', current_date))
                migrated_count += 1
                print(f"  ✅ Migrated {title}: £{price:.2f}")
        
        conn.commit()
        print(f"\n✅ Migrated {migrated_count} existing prices to price_history")
        
    except Exception as e:
        print(f"❌ Error migrating existing prices: {e}")
        conn.rollback()
    finally:
        conn.close()

def add_price_history_entry(game_id, price, price_source):
    """Add a new price history entry for a game"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("""
            INSERT INTO price_history (game_id, price, price_source, date_recorded)
            VALUES (?, ?, ?, ?)
        """, (game_id, price, price_source, current_date))
        
        conn.commit()
        print(f"✅ Added price history: Game {game_id}, £{price:.2f} from {price_source}")
        
    except Exception as e:
        print(f"❌ Error adding price history: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_price_history(game_id):
    """Get price history for a specific game"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT price, price_source, date_recorded
            FROM price_history
            WHERE game_id = ?
            ORDER BY date_recorded ASC
        """, (game_id,))
        
        history = cursor.fetchall()
        return history
        
    except Exception as e:
        print(f"❌ Error getting price history: {e}")
        return []
    finally:
        conn.close()

if __name__ == "__main__":
    print("🎮 Setting up Price History Tracking...")
    create_price_history_table()
    migrate_existing_prices()
    
    # Test the functionality
    print("\n🧪 Testing price history functionality...")
    
    # Add a test entry if we have games
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM games LIMIT 1")
    test_game = cursor.fetchone()
    
    if test_game:
        game_id, title = test_game
        print(f"\n📈 Testing with game: {title} (ID: {game_id})")
        
        # Get existing history
        history = get_price_history(game_id)
        print(f"  Current price history entries: {len(history)}")
        
        for price, source, date in history:
            print(f"    £{price:.2f} from {source} on {date}")
    
    conn.close()
    print("\n✅ Price history setup complete!")
