from http.server import BaseHTTPRequestHandler
from api._shared import health_payload, send_json


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        send_json(self, 200, health_payload())

    def log_message(self, format, *args):
        return
