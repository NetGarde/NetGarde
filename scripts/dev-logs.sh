#!/usr/bin/env bash
# Tail local test stack logs (default: backend).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env.dev ]]; then
  cp .env.dev.example .env.dev
fi

SERVICE="${1:-backend}"
docker compose -f docker-compose.dev.yml --env-file .env.dev logs -f "$SERVICE"
