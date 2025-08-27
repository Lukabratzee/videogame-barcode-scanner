#!/usr/bin/env python3
"""
Add Price Region Column Migration

This migration adds the price_region column to the game_alert_settings table
to store per-game region preferences for PriceCharting.
"""

import sqlite3
import os
import sys

def resolve_db_path() -> str:
    """Resolve database path at runtime"""
    if 'DATABASE_PATH' in os.environ and os.environ['DATABASE_PATH'].strip():
        path = os.environ['DATABASE_PATH'].strip()
        if not os.path.isabs(path):
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            path = os.path.join(base, path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path
    # Default to ../data/games.db (same as backend)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, '..', 'data', 'games.db')

def run_migration():
    """Execute the price region column migration"""

    print("🔧 Starting Price Region Column Migration")

    db_path = resolve_db_path()
    print(f"📍 Database: {db_path}")

    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='game_alert_settings'")
        if not cursor.fetchone():
            print("❌ game_alert_settings table does not exist! Run add_price_alert_settings.py first.")
            return False

        # Check if price_region column already exists
        cursor.execute("PRAGMA table_info(game_alert_settings)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'price_region' in columns:
            print("✅ price_region column already exists")
            return True

        print("\n📋 Adding price_region column...")

        # Add the price_region column
        cursor.execute("""
            ALTER TABLE game_alert_settings
            ADD COLUMN price_region VARCHAR(10) DEFAULT 'PAL'
        """)

        conn.commit()
        conn.close()

        print("✅ Added price_region column")
        print("🎉 Migration completed successfully!")

        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("Add Price Region Column Migration")
            print()
            print("Usage:")
            print("  python add_price_region.py          # Run migration")
            print("  python add_price_region.py --help   # Show this help")
            print()
            print("This migration adds the price_region column to game_alert_settings")
            print("for storing per-game region preferences for PriceCharting.")
            return

    if run_migration():
        print("✅ Migration completed")
    else:
        print("❌ Migration failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
