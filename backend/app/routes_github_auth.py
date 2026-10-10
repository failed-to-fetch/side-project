import json
import secrets

import httpx
import redis
from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import github_oauth
from app.auth import AuthUser, get_current_user
from app.core.config import get_settings
from app.core.crypto import encrypt
from app.core.db import get_db
from app.core.redis_client import get_redis
from app.models import ProviderConnection

# Connects a signed-in user's GitHub account for repository access.
router = APIRouter(prefix="/auth/github", tags=["github"])

PROVIDER = "github"
STATE_COOKIE = "oauth_state"
STATE_TTL_SECONDS = 600


def _redirect(path: str) -> RedirectResponse:
    resp = RedirectResponse(f"{get_settings().frontend_url}{path}", status_code=302)
    resp.delete_cookie(STATE_COOKIE)
    return resp


def _fail(reason: str) -> RedirectResponse:
    return _redirect(f"/settings?error={reason}")


def _store_tokens(
    conn: ProviderConnection, tokens: github_oauth.TokenSet, login: str | None
) -> None:
    conn.provider_login = login
    conn.access_token_enc = encrypt(tokens.access_token)
    conn.refresh_token_enc = encrypt(tokens.refresh_token) if tokens.refresh_token else None
    conn.token_expires_at = tokens.expires_at


@router.get("/link")
def github_link(
    current_user: AuthUser = Depends(get_current_user),
    r: redis.Redis = Depends(get_redis),
):
    settings = get_settings()
    if not settings.github_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub is not configured.",
        )
    state = secrets.token_urlsafe(32)
    verifier, challenge = github_oauth.make_pkce()
    r.set(
        f"oauth_state:{state}",
        json.dumps({"verifier": verifier, "user_id": current_user.id}),
        ex=STATE_TTL_SECONDS,
    )
    resp = RedirectResponse(github_oauth.build_authorize_url(state, challenge), status_code=302)
    # Binds this flow to this browser, so a callback URL planted by an attacker is rejected.
    resp.set_cookie(
        STATE_COOKIE, state, max_age=STATE_TTL_SECONDS,
        httponly=True, samesite="lax", secure=settings.cookie_secure,
    )
    return resp


@router.get("/callback")
def github_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oauth_state: str | None = Cookie(default=None, alias=STATE_COOKIE),
    db: Session = Depends(get_db),
    r: redis.Redis = Depends(get_redis),
):
    if error or not code or not state:
        return _fail("github_denied")
    if not oauth_state or not secrets.compare_digest(oauth_state, state):
        return _fail("invalid_state")
    raw = r.getdel(f"oauth_state:{state}")  # single use
    if raw is None:
        return _fail("expired_state")
    flow = json.loads(raw)
    user_id = flow["user_id"]

    try:
        tokens = github_oauth.exchange_code(code, flow["verifier"])
        profile = github_oauth.fetch_profile(tokens.access_token)
    except (httpx.HTTPError, github_oauth.GitHubAuthError):
        return _fail("github_error")

    provider_user_id = str(profile["id"])  # match on the numeric id, not the login
    taken = db.scalar(
        select(ProviderConnection).where(
            ProviderConnection.provider == PROVIDER,
            ProviderConnection.provider_user_id == provider_user_id,
        )
    )
    if taken is not None and taken.user_id != user_id:
        return _fail("already_linked")

    # Reuse the user's existing row, so linking a different GitHub account replaces it.
    conn = taken or db.scalar(
        select(ProviderConnection).where(
            ProviderConnection.user_id == user_id,
            ProviderConnection.provider == PROVIDER,
        )
    )
    if conn is None:
        conn = ProviderConnection(user_id=user_id, provider=PROVIDER)
        db.add(conn)
    conn.provider_user_id = provider_user_id
    _store_tokens(conn, tokens, profile.get("login"))
    try:
        db.commit()
    except IntegrityError:  # lost a race with another user linking the same account
        db.rollback()
        return _fail("already_linked")
    return _redirect("/settings?linked=github")


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def unlink_github(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    conn = db.scalar(
        select(ProviderConnection).where(
            ProviderConnection.user_id == current_user.id,
            ProviderConnection.provider == PROVIDER,
        )
    )
    if conn is None:
        raise HTTPException(status_code=404, detail="GitHub is not linked.")
    db.delete(conn)
    db.commit()
