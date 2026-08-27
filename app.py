"""FastAPI app for Vercel. File is app.py so / is not a .py download."""
import os
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

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
except Exception as exc:
    ops_version = "n/a"
    _ops_error = str(exc)


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
