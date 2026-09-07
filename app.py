import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

APP_VERSION = "2026.09.07-3"

app = Flask(__name__)


@app.context_processor
def inject_version():
    return {"version": APP_VERSION}

app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

_lock = Lock()
_store_path = Path(os.environ.get("STORE_PATH", "data/store.json"))

DEFAULT = {
    "checks": {"test": False, "sonar": False, "deploy": False},
    "notes": [],
    "updated": None,
}


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _load():
    if not _store_path.exists():
        return json.loads(json.dumps(DEFAULT))
    try:
        data = json.loads(_store_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return json.loads(json.dumps(DEFAULT))
    data.setdefault("checks", dict(DEFAULT["checks"]))
    data.setdefault("notes", [])
    data.setdefault("updated", None)
    return data


def _save(data):
    data["updated"] = _now()
    _store_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _store_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(_store_path)


@app.get("/")
def home():
    q = (request.args.get("q") or "").strip().lower()
    with _lock:
        data = _load()
    notes = data["notes"]
    if q:
        notes = [n for n in notes if q in n.get("text", "").lower() or q in n.get("author", "").lower()]
    checks = data["checks"]
    done = sum(1 for v in checks.values() if v)
    return render_template(
        "index.html",
        title="Home",
        notes=notes,
        checks=checks,
        done=done,
        total=len(checks),
        q=q,
        updated=data.get("updated"),
        note_count=len(data["notes"]),
    )


@app.post("/notes")
def add_note():
    text = (request.form.get("text") or "").strip()
    author = (request.form.get("author") or "operator").strip()[:40]
    if not text:
        flash("Note cannot be empty.")
        return redirect(url_for("home"))
    with _lock:
        data = _load()
        data["notes"].insert(
            0,
            {"id": uuid4().hex[:8], "text": text[:500], "author": author, "at": _now()},
        )
        data["notes"] = data["notes"][:50]
        _save(data)
    flash("Note saved.")
    return redirect(url_for("home"))


@app.post("/notes/<note_id>/delete")
def delete_note(note_id):
    with _lock:
        data = _load()
        data["notes"] = [n for n in data["notes"] if n.get("id") != note_id]
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
        for key in data["checks"]:
            data["checks"][key] = request.form.get(key) == "on"
        _save(data)
    flash("Checklist updated.")
    return redirect(url_for("home"))


@app.post("/checks/reset")
def reset_checks():
    with _lock:
        data = _load()
        data["checks"] = {"test": False, "sonar": False, "deploy": False}
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
    return jsonify(
        {
            "status": "ok",
            "service": "test-webapp",
            "time": _now(),
            "notes": len(data["notes"]),
            "checks_done": sum(1 for v in data["checks"].values() if v),
            "updated": data.get("updated"),
            "version": APP_VERSION,
        }
    )


@app.get("/export.json")
def export_json():
    with _lock:
        data = _load()
    return jsonify(data)


@app.get("/health/ui")
def health_ui():
    with _lock:
        data = _load()
    payload = {
        "status": "ok",
        "service": "test-webapp",
        "time": _now(),
        "notes": len(data["notes"]),
        "checks_done": sum(1 for v in data["checks"].values() if v),
        "updated": data.get("updated"),
    }
    return render_template("health.html", title="Health", payload=payload)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
