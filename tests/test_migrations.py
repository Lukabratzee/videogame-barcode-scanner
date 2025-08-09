import os
import sqlite3


def _with_temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "games.db"
    # Point DATABASE_PATH to the temp file (relative for parity with scripts)
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    return str(db_path)


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def test_full_migration_flow(monkeypatch, tmp_path):
    # Arrange: use temp DB
    db_path = _with_temp_db(monkeypatch, tmp_path)

    # Import migration modules after env is set
    import importlib

    # Base setup
    db_setup = importlib.import_module("backend.database_setup")
    # Gallery migration
    gallery_migration = importlib.import_module("backend.migrate_gallery_v1")
    # Price history
    price_history = importlib.import_module("backend.add_price_history")
    # Artwork columns
    artwork_migration = importlib.import_module("backend.migrate_artwork_columns")

    # Act: run in order
    # database_setup.py runs on import via main; call directly by reusing its side effect
    # Here, we invoke the script-labeled functions by reloading after setting env
    import runpy
    runpy.run_module("backend.database_setup", run_name="__main__")
    assert os.path.exists(db_path)

    # Apply gallery migration
    assert gallery_migration.run_migration()

    # Apply price history migration
    # This module defines functions; ensure they run without error
    price_history.create_price_history_table()

    # Apply artwork columns
    assert artwork_migration.migrate_artwork_columns()

    # Assert: schema contains expected bits
    conn = sqlite3.connect(db_path)
    try:
        assert _table_exists(conn, "games")
        assert _table_exists(conn, "game_gallery_metadata")
        assert _table_exists(conn, "game_tags")
        assert _table_exists(conn, "game_tag_associations")
        assert _table_exists(conn, "gallery_settings")
        assert _table_exists(conn, "price_history")

        for col in (
            "high_res_cover_url",
            "hero_image_url",
            "logo_image_url",
            "icon_image_url",
            "steamgriddb_id",
            "artwork_last_updated",
        ):
            assert _column_exists(conn, "games", col)
    finally:
        conn.close()


