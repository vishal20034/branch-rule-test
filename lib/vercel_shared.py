"""Helpers for Vercel Python functions under /api."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def env_payload():
    return {
        "APP_ENV": os.getenv("APP_ENV", "preview"),
        "APP_NAME": os.getenv("APP_NAME", "operations-api"),
        "APP_SECRET_set": bool(os.getenv("APP_SECRET")),
    }


def health_payload():
    body = {
        "status": "ok",
        "service": os.getenv("APP_NAME", "operations-api"),
        "env": os.getenv("APP_ENV", "preview"),
        "secret_configured": bool(os.getenv("APP_SECRET")),
    }
    try:
        from ops_api.api.app import create_app
        from ops_api import __version__

        body["version"] = __version__
        body["ops"] = create_app().health()
    except Exception as exc:
        body["version"] = "n/a"
        body["ops_import_error"] = str(exc)
    return body


def orders_payload():
    from ops_api.api.app import create_app

    api = create_app()
    env = os.getenv("APP_ENV", "preview")
    return api.place_order(
        order_id=f"WEB-{env}",
        customer_id="C-1",
        items=[("WID-1001", 2), ("CAB-3003", 1)],
    )


def send_json(handler, status, obj):
    data = json.dumps(obj, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(data)
