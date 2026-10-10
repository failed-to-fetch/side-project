#!/usr/bin/env bash
# Run what CI runs for the backend: lint, format check, migration check, tests.
#   scripts/check.sh         check only
#   scripts/check.sh --fix   apply lint fixes and formatting first
set -euo pipefail

cd "$(dirname "$0")/.."

case "${1:-}" in
  "") lint="ruff check . && ruff format --check ." ;;
  --fix) lint="ruff check --fix . && ruff format ." ;;
  -h|--help) sed -n '2,4p' "$0"; exit 0 ;;
  *) echo "Unknown option: $1 (try --help)" >&2; exit 2 ;;
esac

# `run` waits for backend-migrate, so the database is at head before `alembic check`.
docker compose run --rm backend sh -c "
  set -e
  echo '== lint';       $lint
  echo '== migrations'; alembic check
  echo '== tests';      python -m pytest -q
"
