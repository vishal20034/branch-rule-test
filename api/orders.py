from http.server import BaseHTTPRequestHandler
from api._shared import orders_payload, send_json


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            send_json(self, 200, orders_payload())
        except Exception as exc:
            send_json(self, 400, {"error": str(exc)})

    def log_message(self, format, *args):
        return
