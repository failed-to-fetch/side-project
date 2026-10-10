import httpx

from app import auth
from app.auth import SESSION_COOKIES, AuthUser


def test_me_requires_session_cookie(client):
    assert client.get("/users/me").status_code == 401


def test_me_returns_better_auth_user(client, sign_in):
    sign_in("ba_alice", "alice@example.com")
    r = client.get("/users/me")
    assert r.status_code == 200
    assert r.json() == {"id": "ba_alice", "email": "alice@example.com", "name": None}


def test_unknown_session_is_rejected(client, monkeypatch):
    monkeypatch.setattr(auth, "fetch_session_user", lambda cookie: None)
    client.cookies.set(SESSION_COOKIES[0], "expired")
    assert client.get("/users/me").status_code == 401


def test_session_lookup_is_cached(client, monkeypatch):
    calls = []

    def fake_fetch(cookie):
        calls.append(cookie)
        return AuthUser(id="ba_alice", email="alice@example.com")

    monkeypatch.setattr(auth, "fetch_session_user", fake_fetch)
    client.cookies.set(SESSION_COOKIES[0], "tok")
    for _ in range(3):
        assert client.get("/users/me").status_code == 200
    assert len(calls) == 1


def test_auth_service_down_gives_503(client, monkeypatch):
    def down(cookie):
        raise auth.AuthServiceUnavailable

    monkeypatch.setattr(auth, "fetch_session_user", down)
    client.cookies.set(SESSION_COOKIES[0], "tok")
    assert client.get("/users/me").status_code == 503


def _fake_get(monkeypatch, status=200, body="null"):
    seen = {}

    def fake_get(url, params, headers, timeout):
        seen.update(url=url, params=params, headers=headers)
        return httpx.Response(status, text=body, request=httpx.Request("GET", url))

    monkeypatch.setattr(auth.httpx, "get", fake_get)
    return seen


def test_fetch_session_user_parses_better_auth_response(monkeypatch, override_settings):
    override_settings(AUTH_SERVICE_URL="http://auth:3001/")
    seen = _fake_get(
        monkeypatch,
        body='{"session": {"id": "s1"}, "user": {"id": "ba_1", "email": "a@b.co",'
        ' "name": "A", "emailVerified": true}}',
    )
    user = auth.fetch_session_user("better-auth.session_token=abc")
    assert user == AuthUser(id="ba_1", email="a@b.co", name="A")
    assert seen["url"] == "http://auth:3001/api/auth/get-session"
    assert seen["params"] == {"disableRefresh": "true"}  # must not extend the session
    assert seen["headers"] == {"Cookie": "better-auth.session_token=abc"}


def test_fetch_session_user_returns_none_when_signed_out(monkeypatch):
    _fake_get(monkeypatch, body="null")
    assert auth.fetch_session_user("better-auth.session_token=abc") is None


def test_fetch_session_user_raises_when_auth_service_errors(monkeypatch):
    _fake_get(monkeypatch, status=500, body="oops")
    try:
        auth.fetch_session_user("better-auth.session_token=abc")
    except auth.AuthServiceUnavailable:
        pass
    else:
        raise AssertionError("expected AuthServiceUnavailable")
