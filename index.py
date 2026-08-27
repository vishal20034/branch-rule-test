"""Vercel FastAPI entrypoint. Instance MUST be named `app`."""
import os
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

APP_ENV = os.getenv("APP_ENV", "preview")
APP_NAME = os.getenv("APP_NAME", "operations-api")
HAS_SECRET = bool(os.getenv("APP_SECRET"))

app = FastAPI(title=APP_NAME, version="1.0.0")

_ops = None
_ops_error = None
try:
    from ops_api.api.app import create_app as create_ops
    from ops_api import __version__ as ops_version

    _ops = create_ops()
except Exception as exc:  # keep the site up even if domain import fails
    ops_version = "n/a"
    _ops_error = str(exc)


@app.get("/", response_class=HTMLResponse)
def home():
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{APP_NAME}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:640px;margin:48px auto;padding:0 16px;color:#0f172a}}
a{{color:#2563eb}} code{{background:#f1f5f9;padding:2px 6px;border-radius:4px}}
.ok{{color:#15803d;font-weight:700}}
</style></head><body>
<h1>Operations API is live</h1>
<p class="ok">Vercel 404 is fixed. FastAPI is serving this page.</p>
<ul>
<li>env: <code>{APP_ENV}</code></li>
<li>secret configured: <code>{str(HAS_SECRET).lower()}</code></li>
<li>ops version: <code>{ops_version}</code></li>
</ul>
<p>JSON: <a href="/health">/health</a> · <a href="/env-check">/env-check</a> · <a href="/orders/demo">/orders/demo</a></p>
</body></html>"""


@app.get("/health")
def health():
    body = {
        "status": "ok",
        "service": APP_NAME,
        "env": APP_ENV,
        "version": ops_version,
        "secret_configured": HAS_SECRET,
    }
    if _ops is not None:
        body["ops"] = _ops.health()
    if _ops_error:
        body["ops_import_error"] = _ops_error
    return body


@app.get("/env-check")
def env_check():
    return JSONResponse(
        {
            "APP_ENV": APP_ENV,
            "APP_NAME": APP_NAME,
            "APP_SECRET_set": HAS_SECRET,
        }
    )


@app.get("/orders/demo")
def demo_order():
    if _ops is None:
        raise HTTPException(status_code=503, detail=_ops_error or "ops api not loaded")
    try:
        return _ops.place_order(
            order_id=f"WEB-{APP_ENV}",
            customer_id="C-1",
            items=[("WID-1001", 2), ("CAB-3003", 1)],
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
