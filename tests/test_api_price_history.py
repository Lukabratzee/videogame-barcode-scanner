import os
import sqlite3
import runpy
import importlib


def _init_temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "games.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    # Base schema
    runpy.run_module("backend.database_setup", run_name="__main__")
    # Migrations
    gallery = importlib.import_module("backend.migrate_gallery_v1")
    gallery.run_migration()
    price_history = importlib.import_module("backend.add_price_history")
    price_history.create_price_history_table()
    artwork = importlib.import_module("backend.migrate_artwork_columns")
    artwork.migrate_artwork_columns()
    return str(db_path)


def _insert_game(db_path: str, game_id: int = 1234, title: str = "Test Game"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO games (id, title, cover_image, description, publisher, platforms, genres, series, release_date, average_price)
        VALUES (?, ?, '', '', '', '', '', '', '2000-01-01', NULL)
        """,
        (game_id, title),
    )
    conn.commit()
    conn.close()


def test_price_history_post_and_get(monkeypatch, tmp_path):
    db_path = _init_temp_db(monkeypatch, tmp_path)
    _insert_game(db_path, 2222, "History Test")

    # Import backend app and create test client
    appmod = importlib.import_module("backend.app")
    client = appmod.app.test_client()

    # POST a price history entry
    res = client.post(
        "/api/price_history",
        json={"game_id": 2222, "price": 19.99, "price_source": "Manual"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data and data.get("success") is True

    # GET the history
    res2 = client.get("/api/price_history/2222")
    assert res2.status_code == 200
    hist = res2.get_json()
    assert hist and hist.get("success") is True
    assert hist.get("total_entries", 0) >= 1

    # Verify game's average_price updated
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT average_price FROM games WHERE id = 2222")
    row = cur.fetchone()
    conn.close()
    assert row is not None and float(row[0]) == 19.99


