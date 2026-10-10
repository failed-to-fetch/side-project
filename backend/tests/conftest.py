import pytest
import redis as redis_lib
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db, get_engine
from app.core.redis_client import get_redis
from app.features.auth import session as auth
from app.features.auth.session import SESSION_COOKIES, AuthUser
from app.main import app


@pytest.fixture
def override_settings(monkeypatch):
    """Call with env-style overrides, e.g. override_settings(GITHUB_CLIENT_ID="x")."""

    def _override(**values: str):
        for name, value in values.items():
            monkeypatch.setenv(name, value)
        get_settings.cache_clear()
        return get_settings()

    yield _override
    get_settings.cache_clear()


@pytest.fixture
def db():
    connection = get_engine().connect()
    outer = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        autoflush=False,
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()


@pytest.fixture
def redis_client():
    r = redis_lib.Redis.from_url(get_settings().redis_url, db=15, decode_responses=True)
    r.flushdb()
    yield r
    r.flushdb()
    r.close()


@pytest.fixture
def client(db, redis_client):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_redis] = lambda: redis_client
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sign_in(client, monkeypatch):
    """Fake a Better Auth session: sets the session cookie on the client and
    answers the backend's get-session lookup for it. Returns the AuthUser."""
    users: dict[str, AuthUser] = {}

    def fake_fetch(cookie_header: str) -> AuthUser | None:
        return users.get(cookie_header.split("=", 1)[1])

    monkeypatch.setattr(auth, "fetch_session_user", fake_fetch)

    def _sign_in(
        user_id: str = "ba_alice", email: str = "alice@example.com"
    ) -> AuthUser:
        token = f"token-{user_id}"
        users[token] = AuthUser(id=user_id, email=email)
        client.cookies.set(SESSION_COOKIES[0], token)
        return users[token]

    return _sign_in
