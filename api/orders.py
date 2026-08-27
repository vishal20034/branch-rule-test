from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.vercel_shared import orders_payload, send_json


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            send_json(self, 200, orders_payload())
        except Exception as exc:
            send_json(self, 400, {"error": str(exc)})

    def log_message(self, format, *args):
        return
