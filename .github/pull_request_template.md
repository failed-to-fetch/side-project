## What and why

<!-- What does this PR change, and why? Link any related issue. -->

## Changes

<!-- Short list of the main changes. -->

-

## How to test

<!-- Commands or steps a reviewer can run. -->

```sh
# Backend
docker compose run --rm backend python -m pytest -q

# Frontend (adjust the folder and scripts to match your project)
cd frontend
pnpm test
pnpm run lint
pnpm run build
```

## Checklist

**General**
- [ ] Tests added or updated, and the backend tests (`docker compose run --rm backend python -m pytest -q`) and any frontend tests pass
- [ ] No secrets, passwords or tokens committed (`.env` is not in the diff)
- [ ] No unrelated changes or leftover debug code

**API changes** (delete if not applicable)
- [ ] Request and response use Pydantic schemas
- [ ] `password_hash` and other sensitive fields are never returned
- [ ] New routes that need login use `get_current_user`
- [ ] Error statuses are intentional (401, 403, 404, 409, 422)

**Frontend changes** (delete if not applicable)
- [ ] Frontend tests added or updated (unit/component tests for new logic, plus any end-to-end test for a changed user flow) and `pnpm test` passes
- [ ] Lint, type check and production build pass (`pnpm run lint`, `pnpm run build`)
- [ ] Requests to the API send credentials (`credentials: "include"` or `withCredentials: true`)
- [ ] Loading, empty and error states are handled (including 401 redirecting to login, 409 on signup and 422 field errors)
- [ ] Checked manually in the browser against the running backend (login, logout, reload while logged in)
- [ ] No secrets or API keys in frontend code or environment variables exposed to the browser
- [ ] Screenshots or a short recording attached for visible UI changes

**Database migrations** (delete if not applicable)
- [ ] Migration file is under `backend/alembic/versions/` and committed
- [ ] I read the generated migration and checked for `op.drop_table`, `op.drop_column` and other destructive operations
- [ ] `docker compose run --rm backend alembic upgrade head` succeeds on the current schema
- [ ] No `Base.metadata.create_all()` at startup, and no `alembic stamp head` used to hide a problem

**Docker and config** (delete if not applicable)
- [ ] `docker compose build backend` succeeds, and `requirements.txt` is updated for new packages
- [ ] New environment variables are documented and have safe local defaults

## Notes for reviewers

<!-- Trade-offs, follow-ups, or anything you want a second opinion on. -->