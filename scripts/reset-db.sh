#!/usr/bin/env bash
# Delete the local Postgres database and start again from empty. Development only.
# Migrations re-run on start. Also the way to apply a new POSTGRES_PASSWORD.
set -euo pipefail

cd "$(dirname "$0")/.."

project=$(basename "$PWD" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_-')
volume="${COMPOSE_PROJECT_NAME:-$project}_postgres-data"

echo "This permanently deletes the local database ($volume):"
echo "all users, sessions and linked accounts. Redis is kept."
read -r -p 'Type "reset" to continue: ' answer
if [[ $answer != reset ]]; then
  echo "Cancelled."
  exit 1
fi

docker compose down  # containers must be gone before their volume can be removed
if docker volume inspect "$volume" >/dev/null 2>&1; then
  docker volume rm "$volume" >/dev/null
  echo "Deleted $volume"
fi

# With the volume gone, setup.sh can safely generate a POSTGRES_PASSWORD if it's empty.
scripts/setup.sh
docker compose up -d
