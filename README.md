# Name to be Decided

A repository analysis app. Users sign in (email and password, GitHub, GitLab or Bitbucket), connect a code host, and the backend will pull in repositories and analyse their history.

**Current status:** sign-in works through the auth service, and the backend can link a GitHub account for repo access. Repo listing, analysis jobs and most of the frontend are not built yet (see [Status](#status)).

## Stack

- **Auth service (`services/auth`):** Better Auth on Node. Owns users, sign-in and sessions
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Psycopg 3. Checks Better Auth sessions; owns repo access and analysis
- **Database:** PostgreSQL 18, shared by both services
- **Cache:** Redis
- **Runtime:** Docker Compose

## Prerequisites

- Git
- Docker with Compose v2 (`docker compose`, not the older `docker-compose`). Docker Desktop on Windows and macOS, or Docker Engine plus the Compose plugin on Linux.
- A GitHub account (only needed to try GitHub sign-in or repo linking)

A local Python virtual environment is optional. It only helps your editor resolve imports. Everything runs in Docker.

## Set up the project

All commands run from the project root.

The scripts in `scripts/` are bash. On Windows, run them from Git Bash (installed with Git for Windows), not PowerShell.

### 1. Create your `.env`

```sh
scripts/setup.sh
```

This copies `.env.example` to `.env` and generates `TOKEN_ENCRYPTION_KEY`, `BETTER_AUTH_SECRET` and `POSTGRES_PASSWORD`. It's safe to re-run: it never overwrites a value you've set. Back up `TOKEN_ENCRYPTION_KEY`: if you lose it, stored tokens can't be decrypted and users have to re-link GitHub.

It then lists the values you have to fill in yourself, such as the GitHub OAuth App for sign-in (the comments in `.env` explain each one). `.env` is git-ignored. Check with `git check-ignore .env`, which should print `.env`.

### 2. Start the services

```sh
scripts/setup.sh --up        # or: docker compose up -d --build
```

This also applies database migrations: `backend-migrate` and `auth-migrate` run once and exit before the backend and auth service start.

The backend runs with auto-reload for code changes. Changes to `.env` or `docker-compose.yml` need `docker compose up -d backend` to take effect, and dependency changes need `docker compose build backend` first (see [Backend dependencies](#backend-dependencies)).

### 3. Check it works

```sh
curl http://localhost:8000/
docker compose exec postgres psql -U app -d appdb -c "\dt"
```

The first should return `{"message":"Backend is running"}`. The second should list `alembic_version` and `provider_connections` (the backend's tables) alongside Better Auth's `user`, `session`, `account` and `verification`. Interactive API docs are at <http://localhost:8000/docs>.

### 4. Run the tests and linter

```sh
scripts/check.sh          # what CI runs: lint, format check, migration check, tests
scripts/check.sh --fix    # apply lint fixes and formatting first
```

See [`backend/tests/README.md`](backend/tests/README.md) for details. The tests use your local development database inside rolled-back transactions, so they leave no data behind. CI (`.github/workflows/backend.yml`) runs the linter, a migration round trip and the tests on every pull request that touches `backend/`.

## Backend dependencies

Dependencies are managed with [uv](https://docs.astral.sh/uv/): `backend/pyproject.toml` lists them, and `backend/uv.lock` pins exact versions. Commit both together. You don't need uv installed locally; run it in the container:

```sh
docker compose run --rm backend uv add <package>          # runtime dependency
docker compose run --rm backend uv add --dev <package>    # test/lint tool only
docker compose run --rm backend uv lock --upgrade         # upgrade everything within the constraints
docker compose build backend && docker compose up -d backend
```

The image has two targets. Compose uses `dev` (includes pytest and ruff, code bind-mounted). The default `prod` target has runtime dependencies only, copies the code in, and runs as a non-root user.

## Database migrations

Schema changes are managed with Alembic. Never use `Base.metadata.create_all()` at startup, and never use `alembic stamp head` to hide a problem.

### Apply migrations

`docker compose up` applies them automatically through the `backend-migrate` service. To apply them by hand (for example after pulling new migration files while the stack is running):

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

1. Change or add the model in its feature folder (e.g. `backend/app/features/integrations/models.py`). A new model must also be imported in `backend/app/models.py`, or Alembic won't see it.
2. Generate the migration:

```sh
scripts/new-migration.sh "describe the change"
```

3. Open the new file in `backend/alembic/versions/` and **read it before applying**:
   - Look for `op.drop_table`, `op.drop_column` and other destructive operations. Autogenerate emits them for anything that exists in the database but not in the models. That is how the early `test_messages` table was dropped.
   - Alembic can misread expression indexes (indexes on `lower(email)` and similar). Delete any spurious drop and create lines for them.
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

Downgrades can destroy data (for example, dropping a table). Downgrading past "replace users with provider connections" deletes every linked GitHub account. Take a backup first if the data matters.

Alembic only manages tables whose model is registered in `backend/app/models.py`. Better Auth's tables are managed by its own migrations (`auth-migrate` in compose) and are ignored by autogenerate.

### Reset your local database

This deletes all local data, including users, sessions and linked accounts. Use it only on a development machine. It asks you to type `reset` first.

```sh
scripts/reset-db.sh
```

It removes the Postgres volume (Redis is kept), fills in an empty `POSTGRES_PASSWORD` via `setup.sh`, and starts everything again. Migrations re-run on start.

Don't use this to work around a migration problem on data you care about. Fix the migration instead.

### Change the database password

Postgres only reads `POSTGRES_PASSWORD` when its volume is first created. To change it on an existing database without losing data, set the new value in `.env`, then:

```sh
docker compose exec postgres psql -U app -d appdb -c "ALTER USER app PASSWORD 'the-new-password'"
docker compose up -d
```

Replace `the-new-password` with the value from `.env`.

## Set up a GitHub App (for repo access)

There are two separate GitHub registrations:

- **Sign-in** uses a GitHub OAuth App (`GITHUB_LOGIN_CLIENT_ID` / `GITHUB_LOGIN_CLIENT_SECRET`), handled by the auth service.
- **Repo access** uses a GitHub App (`GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET`), handled by the backend. This section covers this one.

Each developer registers their own App, because the callback URL points at `localhost`. Never share client secrets between developers.

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
| Account permissions | none needed |
| Where can this GitHub App be installed | Only on this account |

Click **Create GitHub App**.

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
docker compose exec backend python -c "from app.features.integrations.github.client import get_github_client; print(get_github_client().configured)"
```

This must print `True`.

### 4. Try linking

Sign in through the frontend at <http://localhost:3000> first. Then open <http://localhost:8000/auth/github/link> in the same browser and authorize the App. You will be redirected to `http://localhost:3000/settings?linked=github`.

### Linking errors

If linking fails, the redirect goes to `http://localhost:3000/settings?error=<reason>`:

| Reason | Meaning and fix |
|---|---|
| `github_error` | Wrong client secret, or the App's callback URL doesn't exactly match `http://localhost:8000/auth/github/callback` |
| `already_linked` | That GitHub account is already linked to a different user |
| `invalid_state`, `expired_state` | The flow took over 10 minutes or the cookie was lost. Start again from `/auth/github/link` in the same browser |
| `github_denied` | You cancelled, or GitHub returned an error |

## API overview

Sign-in, sign-out and sessions are handled by the auth service at `http://localhost:3001/api/auth/*` (see the [Better Auth docs](https://www.better-auth.com/docs)). The backend reads the `better-auth.session_token` cookie and asks the auth service who it belongs to, caching the answer in Redis for 60 seconds (`AUTH_SESSION_CACHE_SECONDS`). So a sign-out can take up to a minute to reach the backend.

| Endpoint | Auth | Purpose |
|---|---|---|
| `GET /` | none | health message |
| `GET /users/me` | session | current user, `{id, email, name}` from Better Auth |
| `GET /auth/github/link` | session | start linking GitHub for repo access |
| `GET /auth/github/callback` | none | GitHub redirects here |
| `DELETE /auth/github` | session | unlink GitHub (204, 404 if not linked) |

Errors use `{"detail": ...}`. A 503 means the auth service couldn't be reached.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ERR_EMPTY_RESPONSE` or connection reset on port 8000 | The backend crashed on startup. Run `docker compose logs backend --tail 60` and read the last traceback |
| `validation error for Settings` at startup | A required variable is missing or malformed in `.env` (the error names it). Fix it, then `docker compose up -d backend` |
| `{"detail":"GitHub is not configured."}` | `GITHUB_CLIENT_ID` or `GITHUB_CLIENT_SECRET` is missing in `.env` or not restarted. See step 3 of the GitHub App setup |
| `{"detail":"Authentication service unavailable."}` | The `auth` container is down: `docker compose logs auth --tail 60` |
| `relation "..." does not exist` | Migrations not applied: `docker compose run --rm backend alembic upgrade head` |
| `ModuleNotFoundError` for a package | The image is stale: `docker compose build backend`, then `docker compose up -d backend` |
| Environment change has no effect | Auto-reload does not re-read environment variables: `docker compose up -d backend` |

## Status

**Built**
- Sign-in with email and password, GitHub, GitLab and Bitbucket (auth service)
- Backend checks Better Auth sessions
- Linking and unlinking GitHub for repo access, with encrypted token storage
- Test suite

**Not built yet**
- Serving frontend, auth and backend from one origin (so the browser can call the backend without CORS)
- Most of the frontend
- GitHub repo access (App installation, repo listing, installation tokens)
- Repo cloning and analysis jobs
- Password reset, email verification, login rate limiting