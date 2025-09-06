#!/usr/bin/env python3
"""
Migration: Add date_added column to games table and backfill values.

Adds a TEXT column `date_added` to the `games` table. Existing rows are
backfilled using the earliest `price_history.date_recorded` per game when
available, otherwise set to the current UTC timestamp. Idempotent and safe
to run multiple times.
"""

import os
import sqlite3
from datetime import datetime


def _resolve_database_path() -> str:
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


def migrate_add_date_added_column() -> bool:
    db_path = _resolve_database_path()
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='games'")
        if not cur.fetchone():
            print("❌ date_added migration aborted: games table does not exist yet")
            return False

        # Inspect existing columns
        cur.execute("PRAGMA table_info(games)")
        existing_cols = {row[1] for row in cur.fetchall()}

        added = False
        if "date_added" not in existing_cols:
            cur.execute("ALTER TABLE games ADD COLUMN date_added TEXT")
            added = True

        # Backfill values where NULL
        # Prefer earliest price_history entry if table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='price_history'")
        has_history = bool(cur.fetchone())

        if has_history:
            cur.execute(
                """
                UPDATE games
                SET date_added = (
                    SELECT MIN(date_recorded) FROM price_history ph WHERE ph.game_id = games.id
                )
                WHERE date_added IS NULL
                """
            )

        # For remaining NULLs, set to current UTC timestamp
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "UPDATE games SET date_added = ? WHERE date_added IS NULL",
            (now,),
        )

        # Add index (optional for performance)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_games_date_added ON games(date_added)")

        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"❌ date_added migration error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    ok = migrate_add_date_added_column()
    print("✅ date_added column migration completed" if ok else "❌ date_added column migration failed")

