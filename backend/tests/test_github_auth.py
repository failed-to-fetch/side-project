from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import func, select

from src import github_oauth
from src.models import OAuthIdentity, User

PASSWORD = "correct-horse-battery"


@pytest.fixture
def fake_github(monkeypatch):
    monkeypatch.setattr(github_oauth, "CLIENT_ID", "test-client")
    monkeypatch.setattr(github_oauth, "CLIENT_SECRET", "test-secret")
    fake = {"profile": {"id": 4242, "login": "octocat"}, "email": "octo@example.com"}
    monkeypatch.setattr(
        github_oauth, "exchange_code",
        lambda code, verifier: github_oauth.TokenSet("ghu_test", "ghr_test", None),
    )
    monkeypatch.setattr(github_oauth, "fetch_profile", lambda token: fake["profile"])
    monkeypatch.setattr(
        github_oauth, "fetch_verified_primary_email", lambda token: fake["email"]
    )
    return fake


def _begin(client, path="/auth/github/login"):
    r = client.get(path, follow_redirects=False)
    assert r.status_code == 302
    return parse_qs(urlparse(r.headers["location"]).query)


def _finish(client, state):
    return client.get(
        "/auth/github/callback",
        params={"code": "abc", "state": state},
        follow_redirects=False,
    )


def test_login_redirect_uses_state_and_pkce(client, fake_github):
    qs = _begin(client)
    assert qs["client_id"] == ["test-client"]
    assert qs["code_challenge_method"] == ["S256"]
    assert "state" in qs and "code_challenge" in qs
    assert "oauth_state" in client.cookies


def test_first_login_creates_user_and_session(client, db, fake_github):
    r = _finish(client, _begin(client)["state"][0])
    assert r.status_code == 302 and "error" not in r.headers["location"]
    assert client.get("/users/me").json()["email"] == "octo@example.com"
    identity = db.scalar(
        select(OAuthIdentity).where(OAuthIdentity.provider_user_id == "4242")
    )
    assert identity is not None
    assert identity.access_token_enc != "ghu_test"  # stored encrypted


def test_second_login_reuses_user(client, db, fake_github):
    for _ in range(2):
        _finish(client, _begin(client)["state"][0])
    users = db.scalar(
        select(func.count()).select_from(User)
        .where(func.lower(User.email) == "octo@example.com")
    )
    identities = db.scalar(
        select(func.count()).select_from(OAuthIdentity)
        .where(OAuthIdentity.provider_user_id == "4242")
    )
    assert users == 1 and identities == 1


def test_existing_email_is_not_auto_linked(client, db, fake_github):
    client.post("/users", json={"email": "octo@example.com", "password": PASSWORD})
    r = _finish(client, _begin(client)["state"][0])
    assert "error=account_exists" in r.headers["location"]
    identities = db.scalar(
        select(func.count()).select_from(OAuthIdentity)
        .where(OAuthIdentity.provider_user_id == "4242")
    )
    assert identities == 0
    assert client.get("/users/me").status_code == 401


def test_link_attaches_github_to_logged_in_user(client, db, fake_github):
    alice = client.post(
        "/users", json={"email": "alice@example.com", "password": PASSWORD}
    ).json()
    client.post("/auth/login", json={"email": "alice@example.com", "password": PASSWORD})
    r = _finish(client, _begin(client, "/auth/github/link")["state"][0])
    assert "linked=github" in r.headers["location"]
    assert client.get("/users/me").json()["email"] == "alice@example.com"
    identities = db.scalar(
        select(func.count()).select_from(OAuthIdentity)
        .where(OAuthIdentity.user_id == alice["id"])
    )
    assert identities == 1


def test_bad_state_is_rejected(client, fake_github):
    _begin(client)
    r = _finish(client, "wrong")
    assert "error=invalid_state" in r.headers["location"]
    assert client.get("/users/me").status_code == 401


def test_state_is_single_use(client, fake_github):
    state = _begin(client)["state"][0]
    assert "error" not in _finish(client, state).headers["location"]
    assert "error=" in _finish(client, state).headers["location"]

def test_unlink_blocked_when_github_is_only_login_method(client, fake_github):
    _finish(client, _begin(client)["state"][0])
    assert client.delete("/auth/github").status_code == 409