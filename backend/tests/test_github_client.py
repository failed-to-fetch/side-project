"""GitHubClient against a fake transport: what it sends and how it reads GitHub's replies."""

from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.features.integrations.github.client import GitHubClient, GitHubError


def _client(handler) -> GitHubClient:
    return GitHubClient(
        "cid", "secret", "http://test/callback", transport=httpx.MockTransport(handler)
    )


def test_authorize_url_includes_pkce_and_state():
    url = GitHubClient("cid", "secret", "http://test/callback").authorize_url(
        "st", "chal"
    )
    qs = parse_qs(urlparse(url).query)
    assert qs == {
        "client_id": ["cid"],
        "redirect_uri": ["http://test/callback"],
        "state": ["st"],
        "code_challenge": ["chal"],
        "code_challenge_method": ["S256"],
    }


def test_exchange_code_returns_tokens_with_expiry():
    def handler(request):
        body = parse_qs(request.content.decode())
        assert body["code"] == ["the-code"] and body["code_verifier"] == ["ver"]
        assert body["client_secret"] == ["secret"]
        return httpx.Response(
            200,
            json={
                "access_token": "ghu_x",
                "refresh_token": "ghr_x",
                "expires_in": 28800,
            },
        )

    tokens = _client(handler).exchange_code("the-code", "ver")
    assert tokens.access_token == "ghu_x" and tokens.refresh_token == "ghr_x"
    assert tokens.expires_at is not None


def test_exchange_code_raises_on_error_in_200_response():
    # GitHub reports a bad code as HTTP 200 with an "error" field.
    def handler(request):
        return httpx.Response(
            200,
            json={"error": "bad_verification_code", "error_description": "bad code"},
        )

    with pytest.raises(GitHubError, match="bad code"):
        _client(handler).exchange_code("x", "y")


def test_network_failure_raises_github_error():
    def handler(request):
        raise httpx.ConnectError("down")

    with pytest.raises(GitHubError):
        _client(handler).fetch_profile("tok")


def test_fetch_profile_uses_numeric_id_as_string():
    def handler(request):
        assert request.headers["Authorization"] == "Bearer tok"
        return httpx.Response(200, json={"id": 4242, "login": "octocat"})

    profile = _client(handler).fetch_profile("tok")
    assert profile.id == "4242" and profile.login == "octocat"
