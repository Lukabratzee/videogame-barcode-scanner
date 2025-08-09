import runpy
import importlib
import os
import pytest


def init_app_with_temp_db(monkeypatch, tmp_path):
    db = tmp_path / "games.db"
    monkeypatch.setenv("DATABASE_PATH", str(db))
    runpy.run_module("backend.database_setup", run_name="__main__")
    appmod = importlib.import_module("backend.app")
    return appmod


def test_scan_endpoint_with_mock(monkeypatch, tmp_path):
    appmod = init_app_with_temp_db(monkeypatch, tmp_path)

    # Mock IGDB access token
    monkeypatch.setattr(appmod, "get_igdb_access_token", lambda: "DUMMY_TOKEN", raising=True)
    # Mock barcode lookup to return a title and no price
    monkeypatch.setattr(appmod, "scrape_barcode_lookup", lambda code: ("Dummy Game", None), raising=True)

    # Build fake IGDB-like game dicts
    exact_fake = {
        "name": "Dummy Game",
        "platforms": [{"name": "Nintendo Switch"}],
        "genres": [{"name": "Adventure"}],
        "involved_companies": [{"company": {"name": "Dummy Co"}}],
        "first_release_date": None,
        "cover": {"url": "https://example.com/cover.png"},
    }
    alt_fake = {
        "name": "Dummy Game Alt",
        "platforms": [{"name": "PlayStation 5"}],
        "genres": [{"name": "Action"}],
        "involved_companies": [{"company": {"name": "Alt Co"}}],
        "first_release_date": None,
        "cover": {"url": "https://example.com/cover2.png"},
    }

    def fake_search(game_name, token, max_attempts=30, fuzzy_threshold=60):
        return exact_fake, [alt_fake]

    monkeypatch.setattr(appmod, "search_game_fuzzy_with_alternates", fake_search, raising=True)

    client = appmod.app.test_client()
    resp = client.post("/scan", json={"barcode": "1234567890123"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "exact_match" in data
    assert data["exact_match"].get("name") == "Dummy Game"
    assert data["alternative_matches"]


