"""Vercel entrypoint. FastAPI app instance must be named `app`."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from ops_api.api.app import create_app as create_ops
from ops_api import __version__

APP_ENV = os.getenv("APP_ENV", "local")
APP_NAME = os.getenv("APP_NAME", "operations-api")
# Never log APP_SECRET. Presence only.
HAS_SECRET = bool(os.getenv("APP_SECRET"))

ops = create_ops()
app = FastAPI(title=APP_NAME, version=__version__)


@app.get("/")
@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": APP_NAME,
        "env": APP_ENV,
        "version": __version__,
        "secret_configured": HAS_SECRET,
        "ops": ops.health(),
    }


@app.get("/orders/demo")
def demo_order():
    try:
        result = ops.place_order(
            order_id=f"WEB-{APP_ENV}",
            customer_id="C-1",
            items=[("WID-1001", 2), ("CAB-3003", 1)],
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/env-check")
def env_check():
    """Shows which env this deployment is (Preview vs Production). No secret values."""
    return JSONResponse(
        {
            "APP_ENV": APP_ENV,
            "APP_NAME": APP_NAME,
            "APP_SECRET_set": HAS_SECRET,
        }
    )
