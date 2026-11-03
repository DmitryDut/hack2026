"""Mock authorization: signed session token (HMAC-SHA256), same format as the PX embed token."""

import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import Request

from app.services import config

SECRET = os.getenv("PX_SECRET", "hackathon-demo-secret")
COOKIE = "qod_session"


class NeedLogin(Exception):
    def __init__(self, url: str = "/login") -> None:
        self.url = url


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _sign(body: str) -> str:
    return _b64(hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).digest())


def make_token(payload: dict) -> str:
    body = _b64(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode())
    return f"{body}.{_sign(body)}"


def read_token(token: str | None) -> dict | None:
    if not token or "." not in token:
        return None
    body, signature = token.rsplit(".", 1)
    if not hmac.compare_digest(signature, _sign(body)):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    except ValueError:
        return None
    if payload.get("exp", 0) < time.time():
        return None
    return payload


def authenticate(login: str, password: str) -> dict | None:
    for account in config.load("accounts")["accounts"]:
        if account["login"] == login and account["password"] == password:
            return account
    return None


def issue_session(account: dict) -> str:
    ttl = config.load("accounts").get("session_ttl_hours", 8)
    return make_token(
        {
            "login": account["login"],
            "role": account["role"],
            "name": account["name"],
            "partner_id": account.get("partner_id"),
            "exp": int(time.time() + ttl * 3600),
        }
    )


def current_user(request: Request) -> dict | None:
    return read_token(request.cookies.get(COOKIE))


def require_partner(request: Request) -> dict:
    user = current_user(request)
    if not user:
        raise NeedLogin("/login?info=Сессия истекла, войдите снова")
    if user["role"] != "partner":
        raise NeedLogin("/operator")
    return user


def require_operator(request: Request) -> dict:
    user = current_user(request)
    if not user:
        raise NeedLogin("/login?info=Сессия истекла, войдите снова")
    if user["role"] != "operator":
        raise NeedLogin("/cabinet")
    return user
