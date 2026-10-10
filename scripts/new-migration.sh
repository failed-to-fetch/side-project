#!/usr/bin/env bash
# Generate an Alembic migration from model changes.
#   scripts/new-migration.sh "add repos table"
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ $# -ne 1 || -z $1 ]]; then
  echo 'Usage: scripts/new-migration.sh "describe the change"' >&2
  exit 2
fi

# Autogenerate compares the models with the database, so the database must be
# at head first (`run` waits for backend-migrate to apply pending migrations).
docker compose run --rm backend alembic revision --autogenerate -m "$1"

echo
echo "Read the new file in backend/alembic/versions/ before applying it."
echo "Autogenerate misses some things (renames, data changes); fix them by hand. Then:"
echo "  docker compose run --rm backend alembic upgrade head"
