#!/usr/bin/env python3
"""
Add Price Alert Settings Database Migration

This migration adds per-game price alert settings to the database.
"""

import sqlite3
import os
import sys
from datetime import datetime

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
    """Execute the price alert settings database migration"""

    print("🚀 Starting Price Alert Settings Migration")

    db_path = resolve_db_path()
    print(f"📍 Database: {db_path}")

    if not os.path.exists(db_path):
        print("❌ Database file not found! Please run database_setup.py first.")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")

        print("\n📋 Creating game_alert_settings table...")

        # Create the game_alert_settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_alert_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                price_source VARCHAR(50) DEFAULT NULL,
                price_drop_threshold DECIMAL(5,2) DEFAULT NULL,
                price_increase_threshold DECIMAL(5,2) DEFAULT NULL,
                alert_price_threshold DECIMAL(10,2) DEFAULT NULL,
                alert_value_threshold DECIMAL(10,2) DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
                UNIQUE(game_id)
            )
        """)

        print("✅ Created game_alert_settings table")

        # Add indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_game_alert_settings_game_id
            ON game_alert_settings(game_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_game_alert_settings_enabled
            ON game_alert_settings(enabled)
        """)

        print("✅ Added performance indexes")

        # Create trigger to update the updated_at timestamp
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_game_alert_settings_updated_at
                AFTER UPDATE ON game_alert_settings
            BEGIN
                UPDATE game_alert_settings
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.id;
            END
        """)

        print("✅ Added update timestamp trigger")

        conn.commit()
        conn.close()

        print("\n🎉 Migration completed successfully!")
        print("📊 New table 'game_alert_settings' created with the following columns:")
        print("   - game_id: Foreign key to games table")
        print("   - enabled: Whether alerts are enabled for this game")
        print("   - price_source: Price source to use (overrides global default)")
        print("   - price_drop_threshold: % drop threshold (overrides global)")
        print("   - price_increase_threshold: % increase threshold (overrides global)")
        print("   - alert_price_threshold: Minimum price for alerts (overrides global)")
        print("   - alert_value_threshold: Minimum value change for alerts (overrides global)")

        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def rollback_migration():
    """Rollback the price alert settings migration"""

    print("🔄 Rolling back Price Alert Settings Migration")

    db_path = resolve_db_path()

    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Drop the table and related objects
        cursor.execute("DROP TRIGGER IF EXISTS update_game_alert_settings_updated_at")
        cursor.execute("DROP INDEX IF EXISTS idx_game_alert_settings_enabled")
        cursor.execute("DROP INDEX IF EXISTS idx_game_alert_settings_game_id")
        cursor.execute("DROP TABLE IF EXISTS game_alert_settings")

        conn.commit()
        conn.close()

        print("✅ Migration rolled back successfully!")
        return True

    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        if rollback_migration():
            print("✅ Rollback completed")
        else:
            print("❌ Rollback failed")
            sys.exit(1)
    else:
        if run_migration():
            print("✅ Migration completed")
        else:
            print("❌ Migration failed")
            sys.exit(1)
