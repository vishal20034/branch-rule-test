import os
from datetime import datetime, timezone
from threading import Lock

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

_lock = Lock()
_notes = []
_checks = {"test": False, "sonar": False, "deploy": False}


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


@app.get("/")
def home():
    with _lock:
        notes = list(_notes)
        checks = dict(_checks)
    done = sum(1 for v in checks.values() if v)
    return render_template(
        "index.html",
        title="Home",
        notes=notes,
        checks=checks,
        done=done,
        total=len(checks),
    )


@app.post("/notes")
def add_note():
    text = (request.form.get("text") or "").strip()
    author = (request.form.get("author") or "operator").strip()[:40]
    if not text:
        flash("Note cannot be empty.")
        return redirect(url_for("home"))
    with _lock:
        _notes.insert(0, {"text": text[:500], "author": author, "at": _now()})
        _notes[:] = _notes[:20]
    flash("Note saved on this app instance.")
    return redirect(url_for("home"))


@app.post("/checks")
def save_checks():
    with _lock:
        for key in _checks:
            _checks[key] = request.form.get(key) == "on"
    flash("Checklist updated.")
    return redirect(url_for("home"))


@app.get("/pipeline")
def pipeline():
    with _lock:
        checks = dict(_checks)
    return render_template("pipeline.html", title="Pipeline", checks=checks)


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "test-webapp",
        "time": _now(),
        "notes": len(_notes),
        "checks_done": sum(1 for v in _checks.values() if v),
    })


@app.get("/health/ui")
def health_ui():
    payload = {
        "status": "ok",
        "service": "test-webapp",
        "time": _now(),
        "notes": len(_notes),
        "checks_done": sum(1 for v in _checks.values() if v),
    }
    return render_template("health.html", title="Health", payload=payload)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
