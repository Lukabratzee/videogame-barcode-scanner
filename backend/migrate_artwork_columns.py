#!/usr/bin/env python3
"""
Migration: Add high-resolution artwork columns to the games table

This lifts the schema-altering logic from the artwork fetcher into a
dedicated, idempotent migration so the database is fully prepared at
startup, without relying on runtime code paths.
"""

import os
import sqlite3
from typing import List, Tuple


def _resolve_database_path() -> str:
    """
    Resolve database path similar to backend/app.py so migrations run
    against the same SQLite file in both local and Docker environments.
    """
    # Prefer explicit env var
    db_path = os.getenv("DATABASE_PATH", "").strip()
    if db_path:
        # If relative, make it project-root relative
        if not os.path.isabs(db_path):
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            db_path = os.path.join(project_root, db_path)
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return db_path

    # Fallback to project-root/data/games.db
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    default_path = os.path.join(project_root, "data", "games.db")
    os.makedirs(os.path.dirname(default_path), exist_ok=True)
    return default_path


def migrate_artwork_columns() -> bool:
    """
    Add missing artwork-related columns to the games table (idempotent).
    Returns True on success.
    """
    db_path = _resolve_database_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Desired columns and types
    artwork_columns: List[Tuple[str, str]] = [
        ("high_res_cover_url", "TEXT"),
        ("high_res_cover_path", "TEXT"),
        ("hero_image_url", "TEXT"),
        ("hero_image_path", "TEXT"),
        ("logo_image_url", "TEXT"),
        ("logo_image_path", "TEXT"),
        ("icon_image_url", "TEXT"),
        ("icon_image_path", "TEXT"),
        ("steamgriddb_id", "INTEGER"),
        ("artwork_last_updated", "TIMESTAMP"),
    ]

    try:
        # Inspect current columns
        cursor.execute("PRAGMA table_info(games)")
        existing_cols = {row[1] for row in cursor.fetchall()}  # col name at index 1

        added_any = False
        for column_name, column_type in artwork_columns:
            if column_name not in existing_cols:
                cursor.execute(f"ALTER TABLE games ADD COLUMN {column_name} {column_type}")
                added_any = True

        if added_any:
            conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"❌ Artwork migration error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    ok = migrate_artwork_columns()
    print("✅ Artwork columns migration completed" if ok else "❌ Artwork columns migration failed")

