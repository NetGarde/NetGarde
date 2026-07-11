#!/usr/bin/env bash
# Start the local Mac/laptop test stack (Postgres + Redis + API).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE=(docker compose -f docker-compose.dev.yml --env-file .env.dev)

if [[ ! -f .env.dev ]]; then
  cp .env.dev.example .env.dev
  echo "Created .env.dev from .env.dev.example"
fi

if [[ ! -f frontend/.env.development ]]; then
  cp frontend/.env.development.example frontend/.env.development
  echo "Created frontend/.env.development from frontend/.env.development.example"
fi

echo "Starting trustedge-dev (postgres, redis, backend, trusttwin-api)..."
"${COMPOSE[@]}" up -d --build

echo
echo "Waiting for API health..."
API_PORT="$(grep -E '^DEV_API_PORT=' .env.dev 2>/dev/null | cut -d= -f2- || true)"
API_PORT="${API_PORT:-8000}"
for _ in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null; then
    echo "API is up: http://127.0.0.1:${API_PORT}"
    echo "OpenAPI:   http://127.0.0.1:${API_PORT}/docs"
    break
  fi
  sleep 2
done

if ! curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null; then
  echo "API did not become healthy in time. Logs:"
  "${COMPOSE[@]}" logs --tail=80 backend
  exit 1
fi

REDIS_PORT="$(grep -E '^DEV_REDIS_PORT=' .env.dev 2>/dev/null | cut -d= -f2- || true)"
REDIS_PORT="${REDIS_PORT:-6379}"
TRUSTTWIN_PORT="$(grep -E '^DEV_TRUSTTWIN_API_PORT=' .env.dev 2>/dev/null | cut -d= -f2- || true)"
TRUSTTWIN_PORT="${TRUSTTWIN_PORT:-8080}"

echo "Waiting for TrustTwin ingest API..."
for _ in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:${TRUSTTWIN_PORT}/healthz" >/dev/null; then
    echo "TrustTwin API is up: http://127.0.0.1:${TRUSTTWIN_PORT}"
    break
  fi
  sleep 2
done

cat <<EOF

Next steps
----------
Dashboard (host):
  cd frontend && npm install && npm start
  → http://localhost:3000

TrustTwin laptop agent (optional, API already in compose):
  cd ../TrustTwin
  TRUSTTWIN_API_URL=http://127.0.0.1:${TRUSTTWIN_PORT} go run ./cmd/trusttwin

Useful commands
---------------
  ./scripts/dev-logs.sh
  ./scripts/dev-down.sh
  ${COMPOSE[*]} ps
  ${COMPOSE[*]} logs -f trusttwin-api

EOF
