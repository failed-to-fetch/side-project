"""HTTP calls to GitHub, and nothing else. No database, Redis or FastAPI here."""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
API_URL = "https://api.github.com"


class GitHubError(Exception):
    """GitHub was unreachable, returned an error, or rejected the request."""


@dataclass
class TokenSet:
    access_token: str
    refresh_token: str | None
    expires_at: datetime | None


@dataclass
class GitHubProfile:
    id: str  # numeric id as a string; stable, unlike the login
    login: str | None


def make_pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


class GitHubClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        transport: httpx.BaseTransport | None = None,  # for tests
    ):
        self.client_id = client_id
        self._client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._transport = transport

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self._client_secret)

    def _http(self) -> httpx.Client:
        return httpx.Client(transport=self._transport, timeout=10)

    def authorize_url(self, state: str, code_challenge: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{AUTHORIZE_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, code_verifier: str) -> TokenSet:
        try:
            with self._http() as http:
                r = http.post(
                    TOKEN_URL,
                    headers={"Accept": "application/json"},
                    data={
                        "client_id": self.client_id,
                        "client_secret": self._client_secret,
                        "code": code,
                        "redirect_uri": self.redirect_uri,
                        "code_verifier": code_verifier,
                    },
                )
                r.raise_for_status()
                data = r.json()
        except (httpx.HTTPError, ValueError) as e:
            raise GitHubError("token exchange failed") from e
        # GitHub reports failures as HTTP 200 with an "error" field.
        if "error" in data or "access_token" not in data:
            raise GitHubError(data.get("error_description", "token exchange failed"))
        expires_at = None
        if data.get("expires_in"):
            expires_at = datetime.now(UTC) + timedelta(seconds=int(data["expires_in"]))
        return TokenSet(data["access_token"], data.get("refresh_token"), expires_at)

    def fetch_profile(self, token: str) -> GitHubProfile:
        try:
            with self._http() as http:
                r = http.get(
                    f"{API_URL}/user",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                )
                r.raise_for_status()
                data = r.json()
        except (httpx.HTTPError, ValueError) as e:
            raise GitHubError("profile fetch failed") from e
        return GitHubProfile(id=str(data["id"]), login=data.get("login"))


def get_github_client() -> GitHubClient:
    settings = get_settings()
    return GitHubClient(
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret.get_secret_value(),
        redirect_uri=settings.github_redirect_uri,
    )
