import hashlib

import httpx
import redis
from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict

from app.core.config import get_settings
from app.core.redis_client import get_redis

# Set by Better Auth; it adds the __Secure- prefix when served over HTTPS.
SESSION_COOKIES = ("better-auth.session_token", "__Secure-better-auth.session_token")
CACHE_PREFIX = "auth_session:"


class AuthUser(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str  # Better Auth "user".id
    email: str
    name: str | None = None


class AuthServiceUnavailable(Exception):
    pass


def fetch_session_user(cookie_header: str) -> AuthUser | None:
    """Ask Better Auth who owns this session. None means not signed in."""
    try:
        r = httpx.get(
            f"{get_settings().auth_service_url}/api/auth/get-session",
            # Read-only check: a backend call must not extend the session.
            params={"disableRefresh": "true"},
            headers={"Cookie": cookie_header},
            timeout=5,
        )
        r.raise_for_status()
        data = r.json()
    except (httpx.HTTPError, ValueError) as e:
        raise AuthServiceUnavailable from e
    if not data or not data.get("user"):
        return None
    return AuthUser.model_validate(data["user"])


def get_current_user(
    request: Request,
    r: redis.Redis = Depends(get_redis),
) -> AuthUser:
    cookies = [
        f"{n}={request.cookies[n]}" for n in SESSION_COOKIES if n in request.cookies
    ]
    if not cookies:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated.")
    cookie_header = "; ".join(cookies)

    key = CACHE_PREFIX + hashlib.sha256(cookie_header.encode()).hexdigest()
    if (cached := r.get(key)) is not None:
        return AuthUser.model_validate_json(cached)

    try:
        user = fetch_session_user(cookie_header)
    except AuthServiceUnavailable as e:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Authentication service unavailable."
        ) from e
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated.")
    r.set(key, user.model_dump_json(), ex=get_settings().auth_session_cache_seconds)
    return user
