#!/usr/bin/env python3
"""
Database migration script to add youtube_trailer_url column to games table
"""

import sqlite3
import os
import sys

# Add the parent directory to the path so we can import modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

def add_youtube_trailer_column():
    """Add youtube_trailer_url column to the games table"""
    
    # Database path
    db_path = os.path.join(current_dir, "games.db")
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(games)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'youtube_trailer_url' in columns:
            print("youtube_trailer_url column already exists in games table")
            conn.close()
            return True
        
        # Add the new column
        cursor.execute("""
            ALTER TABLE games 
            ADD COLUMN youtube_trailer_url TEXT
        """)
        
        conn.commit()
        print("Successfully added youtube_trailer_url column to games table")
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(games)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'youtube_trailer_url' in columns:
            print("Column verified successfully")
        else:
            print("Warning: Column may not have been added properly")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Adding youtube_trailer_url column to games table...")
    success = add_youtube_trailer_column()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
        sys.exit(1)
