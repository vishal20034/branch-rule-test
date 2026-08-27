from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.vercel_shared import env_payload, send_json


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        send_json(self, 200, env_payload())

    def log_message(self, format, *args):
        return
