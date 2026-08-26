import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone


class AuthService:
    def __init__(self, secret: str = "dev-secret"):
        self.secret = secret.encode()
        self._users = {}
        self._tokens = {}

    def register(self, username: str, password: str) -> str:
        if not username or len(username) < 3:
            raise ValueError("username too short")
        if not password or len(password) < 8:
            raise ValueError("password must be at least 8 characters")
        if username in self._users:
            raise ValueError("user exists")
        salt = secrets.token_hex(8)
        digest = self._hash(password, salt)
        self._users[username] = {"salt": salt, "digest": digest}
        return username

    def login(self, username: str, password: str) -> str:
        user = self._users.get(username)
        if not user:
            raise ValueError("invalid credentials")
        if not hmac.compare_digest(user["digest"], self._hash(password, user["salt"])):
            raise ValueError("invalid credentials")
        token = secrets.token_urlsafe(24)
        self._tokens[token] = {
            "username": username,
            "exp": datetime.now(timezone.utc) + timedelta(hours=8),
        }
        return token

    def verify(self, token: str) -> str:
        rec = self._tokens.get(token)
        if not rec:
            raise ValueError("invalid token")
        if rec["exp"] < datetime.now(timezone.utc):
            raise ValueError("token expired")
        return rec["username"]

    def _hash(self, password: str, salt: str) -> str:
        return hashlib.sha256(self.secret + salt.encode() + password.encode()).hexdigest()
