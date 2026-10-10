import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
API_URL = "https://api.github.com"


class GitHubAuthError(Exception):
    pass


@dataclass
class TokenSet:
    access_token: str
    refresh_token: str | None
    expires_at: datetime | None


def make_pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def build_authorize_url(state: str, code_challenge: str) -> str:
    settings = get_settings()
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code(code: str, code_verifier: str) -> TokenSet:
    settings = get_settings()
    r = httpx.post(
        TOKEN_URL,
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret.get_secret_value(),
            "code": code,
            "redirect_uri": settings.github_redirect_uri,
            "code_verifier": code_verifier,
        },
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    # GitHub reports failures as HTTP 200 with an "error" field.
    if "error" in data or "access_token" not in data:
        raise GitHubAuthError(data.get("error_description", "token exchange failed"))
    expires_at = None
    if data.get("expires_in"):
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(data["expires_in"]))
    return TokenSet(data["access_token"], data.get("refresh_token"), expires_at)


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def fetch_profile(token: str) -> dict:
    r = httpx.get(f"{API_URL}/user", headers=_headers(token), timeout=10)
    r.raise_for_status()
    return r.json()


def fetch_verified_primary_email(token: str) -> str | None:
    r = httpx.get(f"{API_URL}/user/emails", headers=_headers(token), timeout=10)
    if r.status_code != 200:
        return None
    for item in r.json():
        if item.get("primary") and item.get("verified"):
            return item["email"]
    return None