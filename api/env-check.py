from http.server import BaseHTTPRequestHandler
from api._shared import env_payload, send_json


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        send_json(self, 200, env_payload())

    def log_message(self, format, *args):
        return
