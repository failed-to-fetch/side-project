import json
import secrets

import httpx
import redis
from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import github_oauth
from app.auth import get_current_user
from app.core.config import get_settings
from app.core.crypto import encrypt
from app.core.db import get_db
from app.core.redis_client import get_redis
from app.models import OAuthIdentity, User
from app.sessions import create_session, set_session_cookie

router = APIRouter(prefix="/auth/github", tags=["auth"])

STATE_COOKIE = "oauth_state"
STATE_TTL_SECONDS = 600


def _redirect(url: str) -> RedirectResponse:
    resp = RedirectResponse(url, status_code=302)
    resp.delete_cookie(STATE_COOKIE)
    return resp


def _fail(reason: str) -> RedirectResponse:
    return _redirect(f"{get_settings().frontend_url}/login?error={reason}")


def _start(r: redis.Redis, link_user_id: int | None) -> RedirectResponse:
    settings = get_settings()
    if not settings.github_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub sign-in is not configured.",
        )
    state = secrets.token_urlsafe(32)
    verifier, challenge = github_oauth.make_pkce()
    r.set(
        f"oauth_state:{state}",
        json.dumps({"verifier": verifier, "link_user_id": link_user_id}),
        ex=STATE_TTL_SECONDS,
    )
    resp = RedirectResponse(github_oauth.build_authorize_url(state, challenge), status_code=302)
    # Binds this flow to this browser, so a callback URL planted by an attacker is rejected.
    resp.set_cookie(
        STATE_COOKIE, state, max_age=STATE_TTL_SECONDS,
        httponly=True, samesite="lax", secure=settings.cookie_secure,
    )
    return resp


def _store_tokens(identity: OAuthIdentity, tokens: github_oauth.TokenSet, login: str | None) -> None:
    identity.provider_login = login
    identity.access_token_enc = encrypt(tokens.access_token)
    identity.refresh_token_enc = encrypt(tokens.refresh_token) if tokens.refresh_token else None
    identity.token_expires_at = tokens.expires_at


@router.get("/login")
def github_login(r: redis.Redis = Depends(get_redis)):
    return _start(r, None)


@router.get("/link")
def github_link(
    current_user: User = Depends(get_current_user),
    r: redis.Redis = Depends(get_redis),
):
    return _start(r, current_user.id)


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

    try:
        tokens = github_oauth.exchange_code(code, flow["verifier"])
        profile = github_oauth.fetch_profile(tokens.access_token)
    except (httpx.HTTPError, github_oauth.GitHubAuthError):
        return _fail("github_error")

    provider_user_id = str(profile["id"])  # match on the numeric id, not the login
    login = profile.get("login")
    identity = db.scalar(
        select(OAuthIdentity).where(
            OAuthIdentity.provider == "github",
            OAuthIdentity.provider_user_id == provider_user_id,
        )
    )

    # Linking to an already logged-in user
    if flow["link_user_id"] is not None:
        if identity is not None and identity.user_id != flow["link_user_id"]:
            return _fail("already_linked")
        if identity is None:
            identity = OAuthIdentity(
                user_id=flow["link_user_id"],
                provider="github",
                provider_user_id=provider_user_id,
            )
            db.add(identity)
        _store_tokens(identity, tokens, login)
        db.commit()
        return _redirect(f"{get_settings().frontend_url}/settings?linked=github")

    # Logging in
    if identity is not None:
        user = db.get(User, identity.user_id)
        _store_tokens(identity, tokens, login)
        db.commit()
    else:
        email = github_oauth.fetch_verified_primary_email(tokens.access_token)
        if email is None:
            return _fail("no_verified_email")
        exists = db.scalar(select(User).where(func.lower(User.email) == email.lower()))
        if exists is not None:
            # Don't merge accounts by email: log in normally, then use "Connect GitHub".
            return _fail("account_exists")
        user = User(email=email, password_hash=None)
        db.add(user)
        try:
            db.flush()
            identity = OAuthIdentity(
                user_id=user.id, provider="github", provider_user_id=provider_user_id
            )
            _store_tokens(identity, tokens, login)
            db.add(identity)
            db.commit()
        except IntegrityError:
            db.rollback()
            return _fail("account_exists")

    resp = _redirect(get_settings().frontend_url)
    set_session_cookie(resp, create_session(r, user.id))
    return resp


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def unlink_github(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    identity = db.scalar(
        select(OAuthIdentity).where(
            OAuthIdentity.user_id == current_user.id,
            OAuthIdentity.provider == "github",
        )
    )
    if identity is None:
        raise HTTPException(status_code=404, detail="GitHub is not linked.")
    others = db.scalar(
        select(func.count()).select_from(OAuthIdentity).where(
            OAuthIdentity.user_id == current_user.id,
            OAuthIdentity.provider != "github",
        )
    )
    if not current_user.password_hash and not others:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Set a password or link another provider before unlinking GitHub.",
        )
    db.delete(identity)
    db.commit()