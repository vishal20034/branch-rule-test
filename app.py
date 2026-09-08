import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFProtect

APP_VERSION = "2026.09.08"
SERVICE_NAME = "test-webapp"
CHECK_KEYS = ("test", "sonar", "deploy")
NOTE_LIMIT = 50

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.urandom(24)
csrf = CSRFProtect(app)

_lock = Lock()
_store_path = Path(os.environ.get("STORE_PATH", "data/store.json"))


def _empty_store():
    return {
        "checks": {key: False for key in CHECK_KEYS},
        "notes": [],
        "updated": None,
    }


@app.context_processor
def inject_version():
    return {"version": APP_VERSION}


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _load():
    if not _store_path.exists():
        return _empty_store()
    try:
        data = json.loads(_store_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_store()
    checks = data.get("checks") or {}
    data["checks"] = {key: bool(checks.get(key)) for key in CHECK_KEYS}
    notes = data.get("notes") or []
    data["notes"] = notes if isinstance(notes, list) else []
    data.setdefault("updated", None)
    return data


def _save(data):
    data["updated"] = _now()
    _store_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _store_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(_store_path)


def _health_payload(data):
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "time": _now(),
        "notes": len(data["notes"]),
        "checks_done": sum(1 for value in data["checks"].values() if value),
        "updated": data.get("updated"),
        "version": APP_VERSION,
    }


@app.get("/")
def home():
    query = (request.args.get("q") or "").strip().lower()
    with _lock:
        data = _load()
    notes = data["notes"]
    if query:
        notes = [
            note
            for note in notes
            if query in note.get("text", "").lower()
            or query in note.get("author", "").lower()
        ]
    checks = data["checks"]
    return render_template(
        "index.html",
        title="Home",
        notes=notes,
        checks=checks,
        done=sum(1 for value in checks.values() if value),
        total=len(checks),
        q=query,
        updated=data.get("updated"),
        note_count=len(data["notes"]),
    )


@app.post("/notes")
def add_note():
    text = (request.form.get("text") or "").strip()
    author = (request.form.get("author") or "operator").strip()[:40] or "operator"
    if not text:
        flash("Note cannot be empty.")
        return redirect(url_for("home"))
    with _lock:
        data = _load()
        data["notes"].insert(
            0,
            {
                "id": uuid4().hex[:8],
                "text": text[:500],
                "author": author,
                "at": _now(),
            },
        )
        data["notes"] = data["notes"][:NOTE_LIMIT]
        _save(data)
    flash("Note saved.")
    return redirect(url_for("home"))


@app.post("/notes/<note_id>/delete")
def delete_note(note_id):
    with _lock:
        data = _load()
        data["notes"] = [note for note in data["notes"] if note.get("id") != note_id]
        _save(data)
    flash("Note deleted.")
    return redirect(url_for("home"))


@app.post("/notes/clear")
def clear_notes():
    with _lock:
        data = _load()
        data["notes"] = []
        _save(data)
    flash("All notes cleared.")
    return redirect(url_for("home"))


@app.post("/checks")
def save_checks():
    with _lock:
        data = _load()
        data["checks"] = {key: request.form.get(key) == "on" for key in CHECK_KEYS}
        _save(data)
    flash("Checklist updated.")
    return redirect(url_for("home"))


@app.post("/checks/reset")
def reset_checks():
    with _lock:
        data = _load()
        data["checks"] = {key: False for key in CHECK_KEYS}
        _save(data)
    flash("Checklist reset.")
    return redirect(url_for("home"))


@app.get("/pipeline")
def pipeline():
    with _lock:
        data = _load()
    return render_template(
        "pipeline.html",
        title="Pipeline",
        checks=data["checks"],
        updated=data.get("updated"),
    )


@app.get("/health")
def health():
    with _lock:
        data = _load()
    return jsonify(_health_payload(data))


@app.get("/export.json")
def export_json():
    with _lock:
        data = _load()
    return jsonify(data)


@app.get("/health/ui")
def health_ui():
    with _lock:
        data = _load()
    return render_template(
        "health.html",
        title="Health",
        payload=_health_payload(data),
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
