#!/usr/bin/env python3
"""
Fix Alert Settings Default Value Migration

This migration fixes the default value for the 'enabled' column in game_alert_settings
to be FALSE (0) instead of TRUE (1).
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
    """Execute the default value fix migration"""

    print("🔧 Starting Alert Settings Default Fix Migration")

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

        print("\n📋 Fixing default value for enabled column...")

        # SQLite doesn't support changing column defaults directly with ALTER TABLE
        # We need to recreate the table with the new default

        # First, backup existing data
        cursor.execute("SELECT * FROM game_alert_settings")
        existing_data = cursor.fetchall()

        # Get column names
        cursor.execute("PRAGMA table_info(game_alert_settings)")
        columns = [col[1] for col in cursor.fetchall()]

        # Drop the existing table
        cursor.execute("DROP TABLE game_alert_settings")

        # Recreate with correct default
        cursor.execute("""
            CREATE TABLE game_alert_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                enabled BOOLEAN DEFAULT 0,
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

        # Recreate indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_game_alert_settings_game_id
            ON game_alert_settings(game_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_game_alert_settings_enabled
            ON game_alert_settings(enabled)
        """)

        # Recreate trigger
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_game_alert_settings_updated_at
                AFTER UPDATE ON game_alert_settings
            BEGIN
                UPDATE game_alert_settings
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.id;
            END
        """)

        # Restore data (but set enabled to 0 for new default)
        if existing_data:
            for row in existing_data:
                cursor.execute(f"""
                    INSERT INTO game_alert_settings
                    ({', '.join(columns[1:])})
                    VALUES ({', '.join(['?'] * (len(columns) - 1))})
                """, row[1:])  # Skip id column

        conn.commit()
        conn.close()

        print("✅ Fixed default value for enabled column")
        print(f"📊 Restored {len(existing_data)} existing records")
        print("🎉 Migration completed successfully!")

        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def rollback_migration():
    """Rollback the default value fix migration"""
    print("🔄 Rolling back Alert Settings Default Fix Migration")
    print("⚠️  This will restore the table with DEFAULT 1 for enabled column")

    db_path = resolve_db_path()

    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='game_alert_settings'")
        if not cursor.fetchone():
            print("❌ game_alert_settings table does not exist!")
            return False

        # Backup existing data
        cursor.execute("SELECT * FROM game_alert_settings")
        existing_data = cursor.fetchall()

        # Get column names
        cursor.execute("PRAGMA table_info(game_alert_settings)")
        columns = [col[1] for col in cursor.fetchall()]

        # Drop and recreate with old default
        cursor.execute("DROP TABLE game_alert_settings")

        cursor.execute("""
            CREATE TABLE game_alert_settings (
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

        # Restore data
        if existing_data:
            for row in existing_data:
                cursor.execute(f"""
                    INSERT INTO game_alert_settings
                    ({', '.join(columns[1:])})
                    VALUES ({', '.join(['?'] * (len(columns) - 1))})
                """, row[1:])  # Skip id column

        conn.commit()
        conn.close()

        print("✅ Rolled back to DEFAULT 1 for enabled column")
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
