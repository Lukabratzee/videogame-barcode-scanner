import runpy
import importlib
import os
import sqlite3


def _init_db(monkeypatch, tmp_path):
    db = tmp_path / "games.db"
    monkeypatch.setenv("DATABASE_PATH", str(db))
    runpy.run_module("backend.database_setup", run_name="__main__")
    return str(db)


def test_backup_and_list(monkeypatch, tmp_path):
    _init_db(monkeypatch, tmp_path)
    appmod = importlib.import_module("backend.app")
    client = appmod.app.test_client()

    # Create a backup
    res = client.post("/api/backup_db")
    assert res.status_code == 200
    j = res.get_json()
    assert j and j.get("success") is True
    backup_path = j.get("backup_path")
    assert backup_path

    # List backups
    res2 = client.get("/api/backups")
    assert res2.status_code == 200
    j2 = res2.get_json()
    assert j2 and j2.get("success") is True
    assert any(b.get("path") == backup_path for b in j2.get("backups", []))


