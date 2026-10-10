# Name to be Decided

A repository analysis app. Users sign in (email and password, GitHub, GitLab or Bitbucket), connect a code host, and the backend pulls in repositories and analyses their history.

**Status:** sign-in works, and the backend can link a GitHub account for repo access. Repo listing, analysis jobs and most of the frontend are not built yet. See [Status](#status).

## How it fits together

Everything runs in Docker Compose:

| Service | Port | What it does |
|---|---|---|
| `frontend` | <http://localhost:3000> | React app (Vite build served by Caddy) |
| `auth` | <http://localhost:3001> | [Better Auth](https://www.better-auth.com/docs) on Node. Owns users, sign-in and sessions |
| `backend` | <http://localhost:8000/docs> | FastAPI (Python 3.12). Repo access and analysis. Checks sessions with `auth` |
| `postgres` | 5432 | PostgreSQL 18, shared by `auth` and `backend` (each manages only its own tables) |
| `redis` | 6379 | Cache |
| `auth-migrate`, `backend-migrate` | – | Apply database migrations on start, then exit |

Signing in happens in the browser against `auth`, which sets a `better-auth.session_token` cookie. When the backend gets a request with that cookie, it asks `auth` who the user is and caches the answer for 60 seconds.

## Prerequisites

- **Git**
- **Docker** with Compose v2 (`docker compose`, not the older `docker-compose`): Docker Desktop on Windows and macOS, or Docker Engine plus the Compose plugin on Linux
- **A bash shell** for the scripts in `scripts/`. On Windows use **Git Bash** (installed with Git for Windows), not PowerShell
- **A GitHub account**, to create the OAuth App used for sign-in

You don't need Python, Node or uv installed. They run inside the containers.

## Getting started

Run everything from the project root, in Git Bash on Windows.

### 1. Clone

```sh
git clone git@github.com:failed-to-fetch/side-project.git
cd side-project
```

### 2. Create a GitHub OAuth App for sign-in

The auth service won't start without one. Each developer creates their own, because the callback URL points at `localhost`. Never share client secrets.

Go to <https://github.com/settings/applications/new> (Settings, Developer settings, OAuth Apps, New OAuth App):

| Field | Value |
|---|---|
| Application name | anything, e.g. `yourname-side-project-dev` |
| Homepage URL | `http://localhost:3000` |
| Authorization callback URL | `http://localhost:3001/api/auth/callback/github` |

Click **Register application**, then **Generate a new client secret**. Keep the page open: you need the Client ID and the secret in the next step, and GitHub shows the secret only once.

### 3. Create your `.env`

```sh
scripts/setup.sh
```

This creates `.env` from `.env.example` and generates the secrets (`TOKEN_ENCRYPTION_KEY`, `BETTER_AUTH_SECRET`, `POSTGRES_PASSWORD`). Then it lists what you still need to fill in.

Open `.env` and set the two values from step 2:

```dotenv
GITHUB_LOGIN_CLIENT_ID=Ov23liXXXXXXXXXXXXXX
GITHUB_LOGIN_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

No quotes, no spaces around `=`. `.env` is git-ignored; never commit it. Back up `TOKEN_ENCRYPTION_KEY`: if it's lost, stored tokens can't be decrypted and users have to re-link GitHub.

### 4. Start everything

```sh
scripts/setup.sh --up
```

The first run builds all the images, which takes a few minutes. Migrations are applied automatically before the backend and auth service start.

### 5. Check it works

```sh
docker compose ps -a
```

`auth-migrate` and `backend-migrate` should show `Exited (0)`. Everything else should be `Up`, and `backend`, `postgres` and `redis` should be `(healthy)`.

Then open <http://localhost:3000> and sign in with GitHub. The backend API docs are at <http://localhost:8000/docs>.

### 6. Run the checks

```sh
scripts/check.sh
```

This runs what CI runs: lint, a format check, a migration check and the backend tests. All should pass.

### Upgrading from an older checkout

If you set the project up before October 2026 and see `table "test_messages" does not exist`, see [Troubleshooting](#troubleshooting). In short:

```sh
git pull
scripts/setup.sh                 # adds any new .env values
docker compose up -d --build     # rebuilds images and re-runs migrations
```

## Everyday development

```sh
docker compose up -d                     # start (also applies new migrations)
docker compose down                      # stop; your data is kept
docker compose logs -f backend           # follow one service's logs
docker compose ps -a                     # what's running, and migrate results
```

What picks up your changes:

| You changed | What to do |
|---|---|
| Backend code (`backend/app`) | Nothing. The backend auto-reloads |
| A backend migration | `docker compose up -d` (or see [Database migrations](#database-migrations)) |
| Backend dependencies | `docker compose build backend && docker compose up -d` |
| Auth service code (`services/auth`) | `docker compose up -d --build auth` |
| Frontend code | `docker compose up -d --build frontend`, or run Vite with hot reload (below) |
| `.env` or `docker-compose.yml` | `docker compose up -d` (running containers don't re-read them) |

**Frontend with hot reload.** The `frontend` container serves a production build. For hot reload, stop it and run Vite on the same port. The auth service only accepts sign-ins from port 3000. This needs Node 24 and pnpm locally (`mise install` in `frontend/` if you use mise):

```sh
docker compose stop frontend
cd frontend && pnpm install && pnpm dev --port 3000
```

### Scripts

| Script | What it does |
|---|---|
| `scripts/setup.sh [--up]` | Creates `.env` and generates its secrets. Never overwrites values you've set. `--up` also starts everything |
| `scripts/check.sh [--fix]` | Lint, format check, migration check, backend tests. `--fix` applies formatting first |
| `scripts/new-migration.sh "msg"` | Generates an Alembic migration from model changes |
| `scripts/reset-db.sh` | Deletes the local database and starts fresh. Asks you to type `reset` first |

## Backend

The layout and how to add a feature are in [`backend/README.md`](backend/README.md); the tests in [`backend/tests/README.md`](backend/tests/README.md). The tests run against your local database inside transactions that are rolled back, so they leave no data behind.

CI ([`.github/workflows/backend.yml`](.github/workflows/backend.yml)) runs the same checks as `scripts/check.sh` on every pull request that touches `backend/`, plus a migration downgrade and upgrade.

### Dependencies

[uv](https://docs.astral.sh/uv/) manages them: `backend/pyproject.toml` lists them, and `backend/uv.lock` pins exact versions. Commit both together. Run uv inside the container:

```sh
docker compose run --rm backend uv add <package>          # runtime dependency
docker compose run --rm backend uv add --dev <package>    # test or lint tool only
docker compose run --rm backend uv lock --upgrade         # upgrade within the constraints
docker compose build backend && docker compose up -d
```

The backend image has two targets. Compose uses `dev` (with pytest and ruff, code bind-mounted). The default `prod` target has runtime dependencies only and runs as a non-root user.

## Database migrations

The backend's schema is managed with Alembic, and Better Auth's tables by its own migrations (`auth-migrate`). Alembic ignores Better Auth's tables. Never use `Base.metadata.create_all()`, and never use `alembic stamp head` to hide a problem.

`docker compose up` applies pending migrations automatically. To run Alembic yourself:

```sh
docker compose run --rm backend alembic upgrade head    # apply
docker compose run --rm backend alembic current         # should end in "(head)"
docker compose run --rm backend alembic history
docker compose run --rm backend alembic downgrade -1    # roll back one; can destroy data
```

### Create a migration

1. Change or add the model in its feature folder (e.g. `backend/app/features/integrations/models.py`). A **new** model must also be imported in `backend/app/models.py`, or Alembic won't see it.
2. Generate the migration:
   ```sh
   scripts/new-migration.sh "describe the change"
   ```
3. **Read the new file** in `backend/alembic/versions/` before applying it. Check every `drop_table` and `drop_column`. Autogenerate also misses renames and data changes, and can misread expression indexes (such as one on `lower(email)`).
4. Apply it with `docker compose up -d`, and run `scripts/check.sh`.
5. Commit the migration together with the model change.

### Reset or change the database

`scripts/reset-db.sh` deletes all local data (users, sessions, linked accounts) and starts fresh. Use it only on a development machine, and never to work around a broken migration on data you care about.

Postgres only reads `POSTGRES_PASSWORD` when its volume is first created. To change the password and keep your data, set the new value in `.env`, then:

```sh
docker compose exec postgres psql -U app -d appdb -c "ALTER USER app PASSWORD 'the-new-password'"
docker compose up -d
```

## GitHub App for repo access (optional)

This is separate from the OAuth App used for sign-in. A GitHub **App** lets the backend read a user's repositories. Without one, everything else works and linking returns 503.

1. Go to <https://github.com/settings/apps/new> and fill in:

   | Field | Value |
   |---|---|
   | GitHub App name | anything unique, e.g. `yourname-side-project-dev` |
   | Homepage URL | `http://localhost:3000` |
   | Callback URL | `http://localhost:8000/auth/github/callback` |
   | Expire user authorization tokens | ticked |
   | Webhook, Active | unticked |
   | Repository permissions | Contents: Read-only, Metadata: Read-only |
   | Where can this GitHub App be installed | Only on this account |

2. Click **Create GitHub App**. Copy the **Client ID** (starts with `Iv`, not the numeric App ID), then **Generate a new client secret**.
3. Add both to `.env` as `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET`, then run `docker compose up -d`.
4. Sign in at <http://localhost:3000>, then open <http://localhost:8000/auth/github/link> in the same browser. You should land on `/settings?linked=github`.

If it fails, the redirect ends in `?error=<reason>`:

| Reason | Fix |
|---|---|
| `github_error` | Wrong client secret, or the callback URL isn't exactly `http://localhost:8000/auth/github/callback` |
| `already_linked` | That GitHub account is linked to a different user |
| `invalid_state`, `expired_state` | Took over 10 minutes, or the cookie was lost. Start again in the same browser |
| `github_denied` | You cancelled on GitHub |

## API overview

Sign-in, sign-out and sessions: the auth service at `http://localhost:3001/api/auth/*` ([Better Auth API](https://www.better-auth.com/docs)).

Backend:

| Endpoint | Auth | Purpose |
|---|---|---|
| `GET /` | none | health message |
| `GET /users/me` | session | current user: `{id, email, name}` |
| `GET /auth/github/link` | session | start linking GitHub for repo access |
| `GET /auth/github/callback` | none | GitHub redirects here |
| `DELETE /auth/github` | session | unlink GitHub (204; 404 if not linked) |

Errors use `{"detail": ...}`. 401 means no valid session; 503 means the auth service is unreachable. A sign-out can take up to 60 seconds to reach the backend because of the session cache.

## Troubleshooting

Start with `docker compose ps -a` and `docker compose logs <service> --tail 60`.

| Symptom | Cause and fix |
|---|---|
| `table "test_messages" does not exist` while migrating | Old migrations (before October 2026) tried to drop a table that a fresh database never had. Pull the latest code, which fixes them, then `docker compose up -d --build`. If your database is still stuck, `scripts/reset-db.sh` |
| `service "auth-migrate" didn't complete successfully`; `auth`, `backend` and `frontend` stay `Created` | A required `.env` value is empty. `docker compose logs auth-migrate` names it, usually `GITHUB_LOGIN_CLIENT_ID` or `GITHUB_LOGIN_CLIENT_SECRET`. Fill it in, then `docker compose up -d` |
| `backend-migrate` shows `Exited (1)` | A migration failed: `docker compose logs backend-migrate` |
| Backend logs `validation error for Settings` | A `.env` value is missing or malformed; the error names it. Run `scripts/setup.sh`, then `docker compose up -d` |
| `password authentication failed for user "app"` | `POSTGRES_PASSWORD` in `.env` doesn't match the one the database was created with. See [Reset or change the database](#reset-or-change-the-database) |
| `{"detail":"Authentication service unavailable."}` | `auth` is down: `docker compose logs auth --tail 60` |
| `{"detail":"GitHub is not configured."}` | The optional repo-access GitHub App isn't set up. See [GitHub App for repo access](#github-app-for-repo-access-optional) |
| `relation "..." does not exist` | Migrations didn't run: `docker compose up -d`, then check `backend-migrate` |
| `Bind for 0.0.0.0:3000 failed: port is already allocated` | Something else uses that port (often `pnpm dev`). Stop it, or `docker compose stop frontend` |
| `ModuleNotFoundError` in the backend | The image is older than `uv.lock`: `docker compose build backend && docker compose up -d` |
| A script fails with `$'\r': command not found` | It was checked out with Windows line endings. Run `git rm --cached -r -q . && git reset --hard` (commit your work first) |
| A `.env` change has no effect | Running containers don't re-read it: `docker compose up -d` |

## Status

**Built**
- Sign-in with email and password, GitHub, GitLab and Bitbucket (auth service)
- Backend checks Better Auth sessions
- Linking GitHub for repo access, with tokens encrypted at rest
- Backend tests, lint and CI

**Not built yet**
- Serving frontend, auth and backend from one origin, so the browser can call the backend without CORS
- Most of the frontend
- GitHub repo listing and installation tokens
- Repo cloning and analysis jobs
- Password reset, email verification, login rate limiting
