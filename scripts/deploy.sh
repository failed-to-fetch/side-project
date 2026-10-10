#!/usr/bin/env bash
# Deploy a commit on this machine (run on the server, e.g. by Jenkins over SSH).
#   scripts/deploy.sh             deploy the latest origin/Main
#   scripts/deploy.sh <commit>    deploy a specific commit (also how to roll back)
#
# Only services whose image or config changed are rebuilt and restarted: unchanged
# images come from Docker's build cache, and compose leaves unchanged containers
# running. Migrations run as part of `up`. Exits non-zero if anything fails to
# become healthy, so the CI job fails too.
set -euo pipefail

cd "$(dirname "$0")/.."

ref=${1:-origin/Main}

# Refuse to overwrite edits made by hand on the server. .env is git-ignored, so
# it's never touched.
if [[ -n $(git status --porcelain --untracked-files=no) ]]; then
  echo "Error: tracked files were modified on this machine:" >&2
  git status --short --untracked-files=no >&2
  echo "Commit or discard them (git checkout -- <file>) before deploying." >&2
  exit 1
fi

git fetch --quiet origin
target=$(git rev-parse --quiet --verify "$ref^{commit}") || {
  echo "Error: '$ref' isn't a commit or branch in this repo (after fetching origin)." >&2
  exit 1
}
before=$(git rev-parse HEAD)

# Detached checkout of the exact commit: no merges, no surprises.
git checkout --quiet --detach "$target"
echo "Deploying $(git log -1 --format='%h %s')"
if [[ $before != "$target" ]]; then
  echo "Changed since the last deploy ($(git rev-parse --short "$before")):"
  git diff --stat "$before" "$target" | tail -n 1
fi

# Adds any new .env values (e.g. a newly required secret); never overwrites.
scripts/setup.sh >/dev/null

docker compose up -d --build --remove-orphans --wait --wait-timeout 300

# Drop superseded image layers so the disk doesn't fill up over many deploys.
docker image prune -f >/dev/null

echo "Deployed $(git rev-parse --short HEAD)."
