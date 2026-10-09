# Name to be Decided

A repository analysis app. Users sign in (email and password, or GitHub), and the backend will pull in repositories and analyse their history.

**Current status:** the backend has users, sessions and GitHub sign-in. Repo access, analysis jobs and the frontend are not built yet (see [Status](#status)).

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Psycopg 3
- **Database:** PostgreSQL 18
- **Cache and sessions:** Redis
- **Runtime:** Docker Compose

## Prerequisites

- Git
- Docker with Compose v2 (`docker compose`, not the older `docker-compose`). Docker Desktop on Windows and macOS, or Docker Engine plus the Compose plugin on Linux.
- A GitHub account (only needed to try GitHub sign-in)

A local Python virtual environment is optional. It only helps your editor resolve imports. Everything runs in Docker.

## Set up the project

All commands run from the project root.

### 1. Create your `.env`

```sh
cp .env.example .env        # PowerShell: Copy-Item .env.example .env
```

`.env` is git-ignored. Check with `git check-ignore .env`, which should print `.env`.

### 2. Build the images

```sh
docker compose build
```

### 3. Generate a token encryption key

GitHub tokens are stored encrypted in the database. Generate a key:

```sh
docker compose run --rm backend python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Put the output in `.env` as `TOKEN_ENCRYPTION_KEY=...` (no quotes or spaces). Keep a copy somewhere safe: if you lose the key, stored tokens can't be decrypted and users have to re-link GitHub.

Docker may warn about unset variables on this first run. That is expected until `.env` is filled in.

### 4. Start the services

```sh
docker compose up -d
```

The backend runs with auto-reload for code changes. Changes to `.env` or `docker-compose.yml` need `docker compose up -d backend` to take effect, and changes to `requirements.txt` need `docker compose build backend` first.

### 5. Apply the database migrations

```sh
docker compose run --rm backend alembic upgrade head
```

### 6. Check it works

```sh
curl http://localhost:8000/
docker compose exec postgres psql -U app -d appdb -c "\dt"
```

The first should return `{"message":"Backend is running"}`. The second should list `alembic_version`, `oauth_identities` and `users`. Interactive API docs are at <http://localhost:8000/docs>.

### 7. Run the tests

```sh
docker compose run --rm backend python -m pytest -q
```

See [`backend/tests/README.md`](backend/tests/README.md) for details. The tests use your local development database inside rolled-back transactions, so they leave no data behind.

## Database migrations

Schema changes are managed with Alembic. Never use `Base.metadata.create_all()` at startup, and never use `alembic stamp head` to hide a problem.

### Apply migrations

Run this after cloning, and again after pulling changes that add migration files:

```sh
docker compose run --rm backend alembic upgrade head
```

### Check the current state

```sh
docker compose run --rm backend alembic current    # revision the database is on
docker compose run --rm backend alembic history    # all revisions
```

`alembic current` should show `(head)` when the database is up to date.

### Create a new migration

1. Change the models in `backend/src/models.py`. Every model must be imported there so Alembic can see it.
2. Generate the migration:

```sh
docker compose run --rm backend alembic revision --autogenerate -m "describe the change"
```

3. Open the new file in `backend/alembic/versions/` and **read it before applying**:
   - Look for `op.drop_table`, `op.drop_column` and other destructive operations. Autogenerate emits them for anything that exists in the database but not in the models. That is how the early `test_messages` table was dropped.
   - Alembic can misread expression indexes such as `users_email_lower_unique` (which indexes `lower(email)`). Delete any spurious drop and create lines for it.
4. Apply it:

```sh
docker compose run --rm backend alembic upgrade head
```

5. Commit the migration file together with the model change.

The migration file must appear under `backend/alembic/versions/` on your machine. It does, because `./backend` is bind-mounted into the container.

### Roll back

```sh
docker compose run --rm backend alembic downgrade -1
```

Downgrades can destroy data (for example, dropping a table). The downgrade of the "nullable password hash" change also fails if GitHub-only users exist, since they have no password hash. Take a backup first if the data matters.

### Reset your local database

This deletes all local data, including users and sessions' database rows. Use it only on a development machine.

```sh
docker compose down -v
docker compose up -d
docker compose run --rm backend alembic upgrade head
```

Don't use this to work around a migration problem on data you care about. Fix the migration instead.

## Set up a GitHub App (for GitHub sign-in)

GitHub sign-in uses a GitHub App, not an OAuth App. Each developer registers their own App, because the callback URL points at `localhost`. Never share client secrets between developers.

### 1. Register the App

Go to <https://github.com/settings/apps/new> (GitHub profile picture, then Settings, Developer settings, GitHub Apps, New GitHub App) and fill in:

| Field | Value |
|---|---|
| GitHub App name | anything unique, e.g. `yourname-side-project-dev` |
| Homepage URL | `http://localhost:3000` |
| Callback URL | `http://localhost:8000/auth/github/callback` |
| Expire user authorization tokens | ticked |
| Webhook, Active | unticked (not needed for local development) |
| Repository permissions | Contents: Read-only, Metadata: Read-only |
| Account permissions | **Email addresses: Read-only** |
| Where can this GitHub App be installed | Only on this account |

Click **Create GitHub App**.

The Email addresses permission is required. Without it, sign-in fails with `no_verified_email`.

### 2. Copy the credentials

On the App's settings page:

- **Client ID** is shown near the top. It starts with `Iv`. (This is not the numeric App ID.)
- Under **Client secrets**, click **Generate a new client secret** and copy it immediately. GitHub shows it only once.

Add both to `.env`, with no quotes or spaces:

```dotenv
GITHUB_CLIENT_ID=Iv23liXXXXXXXXXXXXXX
GITHUB_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

You do not need the private key (`.pem`) or the App ID yet. They will be needed later for cloning repositories.

### 3. Restart the backend and verify

```sh
docker compose up -d backend
docker compose exec backend python -c "import os; print(bool(os.getenv('GITHUB_CLIENT_ID')), bool(os.getenv('GITHUB_CLIENT_SECRET')))"
```

This must print `True True`.

### 4. Try signing in

Open <http://localhost:8000/auth/github/login> in your browser and authorize the App. You will be redirected to `http://localhost:3000/`. Until a frontend runs on that port, the browser shows a connection error. That is expected. The session cookie is already set.

Then open <http://localhost:8000/users/me>. You should see your GitHub email as JSON.

### Sign-in errors

If sign-in fails, the redirect goes to `http://localhost:3000/login?error=<reason>`:

| Reason | Meaning and fix |
|---|---|
| `github_error` | Wrong client secret, or the App's callback URL doesn't exactly match `http://localhost:8000/auth/github/callback` |
| `no_verified_email` | The App lacks the Email addresses permission, or your account has no verified primary email. After adding the permission, revoke the App at <https://github.com/settings/apps/authorizations> and sign in again |
| `account_exists` | A password account with the same email exists. Log in with the password, then link GitHub from `/auth/github/link` |
| `invalid_state`, `expired_state` | The flow took over 10 minutes or the cookie was lost. Start again from `/auth/github/login` in the same browser |
| `github_denied` | You cancelled, or GitHub returned an error |

### Remove the test account

```sh
docker compose exec postgres psql -U app -d appdb -c "DELETE FROM users WHERE id IN (SELECT user_id FROM oauth_identities);"
```

This deletes every user that has a linked identity, so use it only on a development database.

## API overview

Sessions use a random token stored (hashed) in Redis and sent as an HttpOnly, SameSite=Lax cookie named `session_id`. Requests from a browser app must include credentials.

| Endpoint | Auth | Purpose |
|---|---|---|
| `GET /` | none | health message |
| `POST /users` | none | register with `{email, password}` (201, 409 duplicate, 422 invalid) |
| `POST /auth/login` | none | log in with email and password, sets the cookie |
| `POST /auth/logout` | cookie | end the session (204) |
| `GET /users/me` | cookie | current user |
| `GET /users/{id}` | cookie | own record only (403 otherwise) |
| `GET /auth/github/login` | none | start GitHub sign-in |
| `GET /auth/github/callback` | none | GitHub redirects here |
| `GET /auth/github/link` | cookie | link GitHub to the logged-in user |
| `DELETE /auth/github` | cookie | unlink GitHub (409 if it is the only login method) |

A user object is `{id, email, created_at, updated_at}`. Errors use `{"detail": ...}`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ERR_EMPTY_RESPONSE` or connection reset on port 8000 | The backend crashed on startup. Run `docker compose logs backend --tail 60` and read the last traceback |
| `ValueError: Fernet key must be 32 url-safe base64-encoded bytes` | `TOKEN_ENCRYPTION_KEY` is missing, empty or malformed in `.env`. Fix it, then `docker compose up -d backend` |
| `{"detail":"GitHub sign-in is not configured."}` | `GITHUB_CLIENT_ID` or `GITHUB_CLIENT_SECRET` is missing in `.env` or not restarted. See step 3 of the GitHub App setup |
| `relation "..." does not exist` | Migrations not applied: `docker compose run --rm backend alembic upgrade head` |
| `ModuleNotFoundError` for a package | The image is stale: `docker compose build backend`, then `docker compose up -d backend` |
| Environment change has no effect | Auto-reload does not re-read environment variables: `docker compose up -d backend` |

## Status

**Built**
- Registration, login, logout, sessions in Redis
- GitHub sign-in, linking and unlinking, with encrypted token storage
- Test suite

**Not built yet**
- CORS configuration for a separate frontend origin (needed before a browser app on `localhost:3000` can call the API)
- The frontend
- GitHub repo access (App installation, repo listing, installation tokens)
- Repo cloning and analysis jobs
- Password reset, email verification, login rate limiting