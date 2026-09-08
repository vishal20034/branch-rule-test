import json
import os
from pathlib import Path

import app as appmod


def _client(tmp_path, monkeypatch):
    store = tmp_path / "store.json"
    monkeypatch.setattr(appmod, "_store_path", store)
    appmod.app.config["WTF_CSRF_ENABLED"] = False
    appmod.app.config["TESTING"] = True
    return appmod.app.test_client()


def test_home_ok(tmp_path, monkeypatch):
    res = _client(tmp_path, monkeypatch).get("/")
    assert res.status_code == 200
    assert b"Operator board" in res.data


def test_add_search_delete_note(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    c.post("/notes", data={"author": "qa", "text": "gate passed"})
    res = c.get("/?q=gate")
    assert b"gate passed" in res.data
    data = json.loads(Path(appmod._store_path).read_text())
    note_id = data["notes"][0]["id"]
    res = c.post(f"/notes/{note_id}/delete", follow_redirects=True)
    assert res.status_code == 200
    left = json.loads(Path(appmod._store_path).read_text())
    assert left["notes"] == []


def test_checks_and_reset(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    c.post("/checks", data={"test": "on", "sonar": "on"})
    data = json.loads(Path(appmod._store_path).read_text())
    assert data["checks"]["test"] is True
    c.post("/checks/reset")
    data = json.loads(Path(appmod._store_path).read_text())
    assert data["checks"]["test"] is False


def test_health_and_export(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    c.post("/notes", data={"author": "qa", "text": "ship it"})
    body = c.get("/health").get_json()
    assert body["status"] == "ok"
    assert body["notes"] == 1
    exported = c.get("/export.json").get_json()
    assert exported["notes"][0]["text"] == "ship it"


def test_health_ui(tmp_path, monkeypatch):
    res = _client(tmp_path, monkeypatch).get("/health/ui")
    assert res.status_code == 200
    assert b"test-webapp" in res.data


def test_pipeline_page(tmp_path, monkeypatch):
    res = _client(tmp_path, monkeypatch).get("/pipeline")
    assert res.status_code == 200
    assert b"pytest" in res.data.lower()
