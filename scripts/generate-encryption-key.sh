#!/usr/bin/env bash
set -euo pipefail

ENV_FILE=".env"

# Ensure the script is run from the repository root.
if [[ ! -f "docker-compose.yml" && ! -f "compose.yml" ]]; then
echo "Error: Run this script from the repository root." >&2
exit 1
fi

# Create .env from the example if it doesn't exist.
if [[ ! -f "$ENV_FILE" ]]; then
if [[ -f ".env.example" ]]; then
cp .env.example "$ENV_FILE"
echo "Created .env from .env.example"
else
touch "$ENV_FILE"
echo "Created .env"
fi
fi

# Preserve an existing, non-empty key.

if grep -q '^TOKEN_ENCRYPTION_KEY=.' "$ENV_FILE"; then
echo "TOKEN_ENCRYPTION_KEY already exists in .env; leaving it unchanged."
exit 0
fi

# Generate a new Fernet key inside the backend container.
KEY=$(docker compose run --rm --no-deps backend python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

if [[ -z "$KEY" ]]; then
echo "Error: Key generation failed." >&2
exit 1
fi

# Append the key without overwriting other environment variables.
printf '\nTOKEN_ENCRYPTION_KEY=%s\n' "$KEY" >> "$ENV_FILE"

echo "Generated TOKEN_ENCRYPTION_KEY and saved it to .env"
echo "Keep this key backed up; do not commit .env to version control."
