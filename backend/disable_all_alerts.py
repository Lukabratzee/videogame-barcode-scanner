#!/usr/bin/env python3
"""
Disable All Game Alerts Migration

This script disables all game alerts by setting enabled=0 for all records
in the game_alert_settings table.
"""

import sqlite3
import os

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

def disable_all_alerts():
    """Disable all game alerts"""

    print("🔧 Disabling All Game Alerts")

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
            print("❌ game_alert_settings table does not exist!")
            return False

        # Count records before update
        cursor.execute("SELECT COUNT(*) FROM game_alert_settings WHERE enabled = 1")
        enabled_count = cursor.fetchone()[0]

        # Disable all alerts
        cursor.execute("UPDATE game_alert_settings SET enabled = 0")

        # Count records after update
        cursor.execute("SELECT COUNT(*) FROM game_alert_settings WHERE enabled = 0")
        disabled_count = cursor.fetchone()[0]

        conn.commit()
        conn.close()

        print(f"✅ Disabled alerts for {enabled_count} games")
        print(f"📊 Total games with disabled alerts: {disabled_count}")
        print("🎉 All game alerts have been disabled!")

        return True

    except Exception as e:
        print(f"❌ Error disabling alerts: {e}")
        return False

if __name__ == "__main__":
    if disable_all_alerts():
        print("✅ All game alerts have been disabled successfully!")
    else:
        print("❌ Failed to disable game alerts")
        exit(1)
