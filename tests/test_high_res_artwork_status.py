import runpy
import importlib
import sqlite3


def _init(monkeypatch, tmp_path):
    db = tmp_path / "games.db"
    monkeypatch.setenv("DATABASE_PATH", str(db))
    runpy.run_module("backend.database_setup", run_name="__main__")
    # Ensure artwork columns exist
    import backend.migrate_artwork_columns as art
    art.migrate_artwork_columns()
    return str(db)


def test_high_res_artwork_status(monkeypatch, tmp_path):
    db_path = _init(monkeypatch, tmp_path)
    # Insert two games, one with artwork, one without
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO games (id, title, cover_image, description, publisher, platforms, genres, series, release_date, average_price,
                           high_res_cover_url)
        VALUES (1, 'With Art', '', '', '', '', '', '', '2000-01-01', NULL, '/media/data/artwork/grids/1.png')
        """
    )
    cur.execute(
        """
        INSERT INTO games (id, title, cover_image, description, publisher, platforms, genres, series, release_date, average_price)
        VALUES (2, 'No Art', '', '', '', '', '', '', '2000-01-01', NULL)
        """
    )
    conn.commit()
    conn.close()

    appmod = importlib.import_module("backend.app")
    # Ensure backend uses the same temporary DB path for this request
    appmod.database_path = db_path
    client = appmod.app.test_client()

    res = client.get("/api/high_res_artwork/status")
    assert res.status_code == 200
    data = res.get_json()
    assert data and data.get("success") is True
    stats = data.get("stats", {})
    assert stats.get("total_games") == 2
    # coverage_percentage should be > 0 and < 100 in this case
    assert 0 < stats.get("coverage_percentage", 0) < 100

