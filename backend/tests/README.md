# Backend tests

Tests for the FastAPI backend. They run inside Docker against the real Postgres and Redis services from `docker-compose.yml`.

## Prerequisites

- Docker with Compose v2 (`docker compose`, not the older `docker-compose`). Docker Desktop on Windows/macOS, or Docker Engine plus the Compose plugin on Linux
- Commands are run from the project root in PowerShell or sh/zsh
- The backend image has been built with the test dependencies (`pytest`, `httpx`) in `backend/requirements.txt`:

```powershell
docker compose build backend
```

Rebuild again whenever `requirements.txt` changes. Code and test changes do not need a rebuild, because `./backend` is bind-mounted into the container at `/app`.

## Run the tests

```powershell
docker compose run --rm backend python -m pytest -q
```

Use `python -m pytest` rather than bare `pytest`. It puts `/app` on the import path so `from app.main import app` works. Compose starts Postgres and Redis automatically (`depends_on`).

Expected result: all tests pass (14 at the time of writing).

## Useful variations

```powershell
# Verbose, one line per test
docker compose run --rm backend python -m pytest -v

# One file
docker compose run --rm backend python -m pytest tests/test_auth_api.py -v

# One test, or tests matching a name
docker compose run --rm backend python -m pytest -k logout -v

# Stop at the first failure and show print output
docker compose run --rm backend python -m pytest -x -s
```

## What is covered

| File | Covers |
|---|---|
| `test_users_api.py` | Creating users, case-insensitive duplicate email (409), password validation (422), auth required to read a user |
| `test_auth_api.py` | Login and HttpOnly session cookie, identical 401 for wrong password and unknown email, `/users/me`, logout revoking the session in Redis, 403 when reading another user |
| `test_updated_at.py` | `updated_at` changes when a user row is updated |
| `conftest.py` | Shared fixtures (see below) |

## How test isolation works

- **Postgres:** the `db` fixture opens a connection, starts a transaction, and rolls it back after each test. Commits inside the app become savepoints, so tests leave no rows behind and never see each other's data.
- **Redis:** the `redis_client` fixture uses database 15 and flushes it before and after each test. Your dev sessions in database 0 are never touched. This assumes `REDIS_URL` has no `/db` suffix, which matches the compose file.
- **Exception:** `test_updated_at.py` commits for real in its own session (Postgres `now()` is fixed for the length of a transaction, so a rolled-back test can't observe it changing). It uses a random email and deletes the row in a `finally` block.

The tests use the same database as development, so don't point them at data you care about without checking the fixtures first.

## Platform notes

- **Windows, macOS, Linux:** the commands are identical. Only the shell differs (PowerShell, zsh, bash).
- **Linux:** files created inside the container (such as `.pytest_cache/` and any Alembic migrations you generate) are owned by root on the host, because the container runs as root against the bind mount. If that gets in the way, `sudo chown -R "$USER" backend` fixes ownership. macOS and Windows with Docker Desktop don't have this issue.
- **Apple Silicon (M-series Macs):** the `python`, Postgres and Redis images are multi-arch, so no changes are needed.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: pytest`, `httpx`, `pwdlib`, or `email_validator` | Image is out of date: `docker compose build backend` |
| `ModuleNotFoundError: app` | Run with `python -m pytest` from the project root, not bare `pytest` |
| `No module named 'psycopg2'` | Use `postgresql+psycopg://...` as `DATABASE_URL` in `docker-compose.yml` |
| `no tests ran` | Test files must live in `backend/tests/` and be named `test_*.py` |
| `KeyError: 'DATABASE_URL'` or `'REDIS_URL'` | Run through `docker compose run`, which supplies the environment variables |
| Duplicate email `IntegrityError` in a test | A leftover row from manual testing: delete it with `docker compose exec postgres psql -U app -d appdb -c "DELETE FROM users WHERE email = '<email>';"` |

The `httpx` deprecation warning from Starlette's `TestClient` is harmless.

## Adding a test

- Use the `client` fixture for API tests. It already isolates Postgres and Redis.
- Sign up through `POST /users` and log in through `POST /auth/login`. The client keeps the session cookie between calls.
- Avoid naming a file `*_test.py` unless it is meant to be collected. Pytest picks up both `test_*.py` and `*_test.py`.