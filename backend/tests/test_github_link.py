from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import func, select

from app.core.crypto import decrypt
from app.features.integrations.github.client import (
    GitHubClient,
    GitHubProfile,
    TokenSet,
    get_github_client,
)
from app.features.integrations.models import ProviderConnection
from app.main import app


class FakeGitHub(GitHubClient):
    def __init__(self):
        super().__init__("test-client", "test-secret", "http://test/callback")
        self.profile = GitHubProfile(id="4242", login="octocat")

    def exchange_code(self, code, code_verifier):
        return TokenSet("ghu_test", "ghr_test", None)

    def fetch_profile(self, token):
        return self.profile


@pytest.fixture
def fake_github(client):
    fake = FakeGitHub()
    app.dependency_overrides[get_github_client] = lambda: fake
    return fake  # the client fixture clears overrides afterwards


def _begin(client):
    r = client.get("/auth/github/link", follow_redirects=False)
    assert r.status_code == 302
    return parse_qs(urlparse(r.headers["location"]).query)


def _finish(client, state):
    return client.get(
        "/auth/github/callback",
        params={"code": "abc", "state": state},
        follow_redirects=False,
    )


def _link(client):
    return _finish(client, _begin(client)["state"][0])


def _connections(db, **where):
    q = select(func.count()).select_from(ProviderConnection)
    for column, value in where.items():
        q = q.where(getattr(ProviderConnection, column) == value)
    return db.scalar(q)


def test_link_requires_sign_in(client, fake_github):
    assert client.get("/auth/github/link", follow_redirects=False).status_code == 401


def test_link_returns_503_when_github_not_configured(client, sign_in):
    sign_in()
    app.dependency_overrides[get_github_client] = lambda: GitHubClient("", "", "")
    assert client.get("/auth/github/link", follow_redirects=False).status_code == 503


def test_link_redirect_uses_state_and_pkce(client, sign_in, fake_github):
    sign_in()
    qs = _begin(client)
    assert qs["client_id"] == ["test-client"]
    assert qs["code_challenge_method"] == ["S256"]
    assert "state" in qs and "code_challenge" in qs
    assert "oauth_state" in client.cookies


def test_callback_stores_encrypted_tokens_for_signed_in_user(
    client, db, sign_in, fake_github
):
    sign_in("ba_alice")
    r = _link(client)
    assert r.headers["location"].endswith("/settings?linked=github")
    conn = db.scalar(
        select(ProviderConnection).where(ProviderConnection.user_id == "ba_alice")
    )
    assert conn.provider_user_id == "4242" and conn.provider_login == "octocat"
    assert conn.access_token_enc != "ghu_test"  # stored encrypted
    assert decrypt(conn.access_token_enc) == "ghu_test"


def test_relinking_updates_the_existing_connection(client, db, sign_in, fake_github):
    sign_in("ba_alice")
    _link(client)
    fake_github.profile = GitHubProfile(id="5555", login="other-account")
    _link(client)
    assert _connections(db, user_id="ba_alice") == 1
    assert _connections(db, provider_user_id="5555") == 1


def test_github_account_linked_to_another_user_is_rejected(
    client, db, sign_in, fake_github
):
    sign_in("ba_alice")
    _link(client)
    sign_in("ba_bob", "bob@example.com")
    r = _link(client)
    assert "error=already_linked" in r.headers["location"]
    assert _connections(db, user_id="ba_bob") == 0


def test_bad_state_is_rejected(client, db, sign_in, fake_github):
    sign_in()
    _begin(client)
    assert "error=invalid_state" in _finish(client, "wrong").headers["location"]
    assert _connections(db) == 0


def test_state_is_single_use(client, sign_in, fake_github):
    sign_in()
    state = _begin(client)["state"][0]
    assert "error" not in _finish(client, state).headers["location"]
    assert "error=" in _finish(client, state).headers["location"]


def test_unlink_removes_connection(client, db, sign_in, fake_github):
    sign_in("ba_alice")
    _link(client)
    assert client.delete("/auth/github").status_code == 204
    assert _connections(db, user_id="ba_alice") == 0
    assert client.delete("/auth/github").status_code == 404
