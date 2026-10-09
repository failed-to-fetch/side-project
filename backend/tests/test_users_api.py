def _payload(email="Alice@Example.com"):
    return {"email": email, "password": "correct-horse-battery"}


def test_create_and_fetch_user(client):
    r = client.post("/users", json=_payload())
    assert r.status_code == 201
    body = r.json()
    assert "password_hash" not in body and "password" not in body

    r2 = client.get(f"/users/{body['id']}")
    assert r2.status_code == 200
    assert r2.json()["email"].lower() == "alice@example.com"


def test_duplicate_email_is_409_case_insensitive(client):
    assert client.post("/users", json=_payload("bob@example.com")).status_code == 201
    r = client.post("/users", json=_payload("BOB@example.com"))
    assert r.status_code == 409


def test_missing_user_is_404(client):
    assert client.get("/users/999999999").status_code == 404


def test_short_password_rejected(client):
    r = client.post("/users", json={"email": "c@example.com", "password": "short"})
    assert r.status_code == 422