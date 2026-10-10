"""Linking a user's GitHub account for repo access. No HTTP or FastAPI here:
callers pass in a DB session, Redis and a GitHubClient."""

import json
import secrets

import redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.crypto import encrypt
from app.features.integrations.github.client import (
    GitHubClient,
    GitHubError,
    TokenSet,
    make_pkce,
)
from app.features.integrations.models import ProviderConnection

PROVIDER = "github"
STATE_TTL_SECONDS = 600


class LinkError(Exception):
    """Linking failed. `reason` is a short code shown to the user."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _state_key(state: str) -> str:
    return f"oauth_state:{state}"


def start_link(r: redis.Redis, github: GitHubClient, user_id: str) -> tuple[str, str]:
    """Begin the OAuth flow. Returns (authorize_url, state); the caller must
    also bind `state` to the browser so the callback can be checked."""
    state = secrets.token_urlsafe(32)
    verifier, challenge = make_pkce()
    r.set(
        _state_key(state),
        json.dumps({"verifier": verifier, "user_id": user_id}),
        ex=STATE_TTL_SECONDS,
    )
    return github.authorize_url(state, challenge), state


def complete_link(
    db: Session,
    r: redis.Redis,
    github: GitHubClient,
    *,
    code: str,
    state: str,
    browser_state: str | None,
) -> ProviderConnection:
    """Finish the OAuth flow and store the user's tokens. Raises LinkError."""
    # The state must match the one bound to this browser, so a callback URL
    # planted by an attacker is rejected.
    if not browser_state or not secrets.compare_digest(browser_state, state):
        raise LinkError("invalid_state")
    raw = r.getdel(_state_key(state))  # single use
    if raw is None:
        raise LinkError("expired_state")
    flow = json.loads(raw)
    user_id = flow["user_id"]

    try:
        tokens = github.exchange_code(code, flow["verifier"])
        profile = github.fetch_profile(tokens.access_token)
    except GitHubError:
        raise LinkError("github_error")

    taken = db.scalar(
        select(ProviderConnection).where(
            ProviderConnection.provider == PROVIDER,
            ProviderConnection.provider_user_id == profile.id,
        )
    )
    if taken is not None and taken.user_id != user_id:
        raise LinkError("already_linked")

    # Reuse the user's existing row, so linking a different GitHub account replaces it.
    conn = taken or _get_connection(db, user_id)
    if conn is None:
        conn = ProviderConnection(user_id=user_id, provider=PROVIDER)
        db.add(conn)
    conn.provider_user_id = profile.id
    _store_tokens(conn, tokens, profile.login)
    try:
        db.commit()
    except IntegrityError:  # lost a race with another user linking the same account
        db.rollback()
        raise LinkError("already_linked")
    return conn


def unlink(db: Session, user_id: str) -> bool:
    """Remove the user's GitHub connection. Returns False if there was none."""
    conn = _get_connection(db, user_id)
    if conn is None:
        return False
    db.delete(conn)
    db.commit()
    return True


def _get_connection(db: Session, user_id: str) -> ProviderConnection | None:
    return db.scalar(
        select(ProviderConnection).where(
            ProviderConnection.user_id == user_id,
            ProviderConnection.provider == PROVIDER,
        )
    )


def _store_tokens(conn: ProviderConnection, tokens: TokenSet, login: str | None) -> None:
    conn.provider_login = login
    conn.access_token_enc = encrypt(tokens.access_token)
    conn.refresh_token_enc = encrypt(tokens.refresh_token) if tokens.refresh_token else None
    conn.token_expires_at = tokens.expires_at
