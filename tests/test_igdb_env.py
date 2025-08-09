import importlib


def test_igdb_env_config(monkeypatch):
    monkeypatch.setenv("IGDB_CLIENT_ID", "abc123")
    monkeypatch.setenv("IGDB_CLIENT_SECRET", "def456")
    # Reload module to pick up env vars
    appmod = importlib.reload(importlib.import_module("backend.app"))
    assert getattr(appmod, "IGDB_CLIENT_ID", "") == "abc123"
    assert getattr(appmod, "IGDB_CLIENT_SECRET", "") == "def456"

