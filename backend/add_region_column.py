#!/usr/bin/env python3
"""
Migration: Add region column to games table

Adds a TEXT column `region` to the `games` table to record whether a game is
from PAL, US, or JP. Existing rows are populated with the default value 'PAL'.
The migration is idempotent and safe to run multiple times.
"""

import os
import sqlite3
from typing import Optional


def _resolve_database_path() -> str:
    """Resolve the same DB path logic used by the app and other migrations."""
    db_path = os.getenv("DATABASE_PATH", "").strip()
    if db_path:
        if not os.path.isabs(db_path):
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            db_path = os.path.join(project_root, db_path)
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return db_path

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    default_path = os.path.join(project_root, "data", "games.db")
    os.makedirs(os.path.dirname(default_path), exist_ok=True)
    return default_path


def migrate_add_region_column() -> bool:
    """Add `region` column to `games` if missing and backfill with 'PAL'."""
    db_path = _resolve_database_path()
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='games'")
        if not cursor.fetchone():
            print("❌ Region migration aborted: games table does not exist yet")
            return False

        # Inspect existing columns
        cursor.execute("PRAGMA table_info(games)")
        existing_cols = {row[1] for row in cursor.fetchall()}  # column name at index 1

        added = False
        if "region" not in existing_cols:
            cursor.execute("ALTER TABLE games ADD COLUMN region TEXT")
            added = True

        if added:
            # Backfill region to 'PAL' for existing rows where NULL or empty
            cursor.execute("UPDATE games SET region = 'PAL' WHERE region IS NULL OR TRIM(IFNULL(region, '')) = ''")
            conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"❌ Region migration error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    ok = migrate_add_region_column()
    print("✅ Region column migration completed" if ok else "❌ Region column migration failed")


