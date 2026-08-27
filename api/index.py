"""Compatibility shim. Real FastAPI app lives in /index.py (Vercel entrypoint)."""
from index import app  # noqa: F401
