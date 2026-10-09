import hashlib
import os
import secrets

import redis

COOKIE_NAME = "session_id"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true" # switch to true if we get https working :)


def _key(token: str) -> str:
    return "session:" + hashlib.sha256(token.encode()).hexdigest()


def create_session(r: redis.Redis, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    r.set(_key(token), str(user_id), ex=SESSION_TTL_SECONDS)
    return token


def get_session_user_id(r: redis.Redis, token: str) -> int | None:
    value = r.get(_key(token))
    return int(value) if value is not None else None


def delete_session(r: redis.Redis, token: str) -> None:
    r.delete(_key(token))