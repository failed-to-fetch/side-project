# backend

FastAPI backend for repo access and analysis. Sign-in is handled by the auth service (`services/auth`); this service checks its sessions.

Setup, migrations and dependencies are covered in the [root README](../README.md); tests in [tests/README.md](tests/README.md).

## Layout

```
app/
  main.py          # app setup, startup/shutdown
  models.py        # registers every model for Alembic
  api/             # shared dependencies (deps.py) and the router list (router.py)
  core/            # config, database, Redis, encryption
  features/<name>/ # one folder per feature: router.py (HTTP), service.py (logic),
                   # client.py (external APIs), models.py (tables)
alembic/           # migrations
tests/
```

To add a feature, create `app/features/<name>/`, register its router in `app/api/router.py`, and any models in `app/models.py`.
