#!/usr/bin/env bash
# Stop the local test stack (keeps Postgres volume unless --wipe).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env.dev ]]; then
  cp .env.dev.example .env.dev
fi

COMPOSE=(docker compose -f docker-compose.dev.yml --env-file .env.dev)

if [[ "${1:-}" == "--wipe" ]]; then
  echo "Stopping trustedge-dev and removing volumes..."
  "${COMPOSE[@]}" down -v
else
  echo "Stopping trustedge-dev (data kept). Use --wipe to drop Postgres volume."
  "${COMPOSE[@]}" down
fi
