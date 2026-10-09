PASSWORD = "correct-horse-battery"


def _signup(client, email="alice@example.com"):
    r = client.post("/users", json={"email": email, "password": PASSWORD})
    assert r.status_code == 201
    return r.json()


def test_login_sets_httponly_cookie(client):
    _signup(client)
    r = client.post("/auth/login", json={"email": "ALICE@example.com", "password": PASSWORD})
    assert r.status_code == 200
    assert "password_hash" not in r.json()
    assert "session_id" in client.cookies
    assert "httponly" in r.headers["set-cookie"].lower()


def test_bad_credentials_give_same_401(client):
    _signup(client)
    wrong_pw = client.post("/auth/login", json={"email": "alice@example.com", "password": "nope-nope-nope"})
    no_user = client.post("/auth/login", json={"email": "ghost@example.com", "password": PASSWORD})
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json() == no_user.json()


def test_me_requires_login(client):
    assert client.get("/users/me").status_code == 401


def test_me_returns_current_user(client):
    _signup(client)
    client.post("/auth/login", json={"email": "alice@example.com", "password": PASSWORD})
    r = client.get("/users/me")
    assert r.status_code == 200
    assert r.json()["email"] == "alice@example.com"


def test_logout_revokes_session_server_side(client):
    _signup(client)
    client.post("/auth/login", json={"email": "alice@example.com", "password": PASSWORD})
    token = client.cookies["session_id"]

    assert client.post("/auth/logout").status_code == 204

    # Replay the old token: Redis must no longer accept it.
    client.cookies.set("session_id", token)
    assert client.get("/users/me").status_code == 401


def test_cannot_read_another_users_record(client):
    alice = _signup(client, "alice@example.com")
    bob = _signup(client, "bob@example.com")
    client.post("/auth/login", json={"email": "alice@example.com", "password": PASSWORD})
    assert client.get(f"/users/{alice['id']}").status_code == 200
    assert client.get(f"/users/{bob['id']}").status_code == 403