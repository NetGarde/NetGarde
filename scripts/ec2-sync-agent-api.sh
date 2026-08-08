#!/usr/bin/env bash
# Enroll token + optional TRUSTEDGE_AGENT_API_IMAGE for compose on EC2.
set -euo pipefail

REPO_ROOT="${TRUSTEDGE_REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
COMPOSE_ENV="${REPO_ROOT}/.env"
TOKEN_FILE="/etc/trustedge/agent-enroll.token"
LEGACY_TOKEN_FILE="/etc/trustedge/trusttwin-enroll.token"

sudo mkdir -p /etc/trustedge

if sudo test -f "$TOKEN_FILE"; then
  TRUSTEDGE_AGENT_ENROLL_TOKEN="$(sudo cat "$TOKEN_FILE" | tr -d '\r\n')"
  echo "Loaded TRUSTEDGE_AGENT_ENROLL_TOKEN from $TOKEN_FILE"
elif sudo test -f "$LEGACY_TOKEN_FILE"; then
  TRUSTEDGE_AGENT_ENROLL_TOKEN="$(sudo cat "$LEGACY_TOKEN_FILE" | tr -d '\r\n')"
  echo "$TRUSTEDGE_AGENT_ENROLL_TOKEN" | sudo tee "$TOKEN_FILE" >/dev/null
  echo "Migrated enroll token from $LEGACY_TOKEN_FILE to $TOKEN_FILE"
else
  TRUSTEDGE_AGENT_ENROLL_TOKEN="$(openssl rand -hex 32)"
  echo "$TRUSTEDGE_AGENT_ENROLL_TOKEN" | sudo tee "$TOKEN_FILE" >/dev/null
  if getent group docker >/dev/null 2>&1; then
    sudo chown root:docker "$TOKEN_FILE"
    sudo chmod 640 "$TOKEN_FILE"
  else
    sudo chmod 600 "$TOKEN_FILE"
  fi
  echo "Generated TRUSTEDGE_AGENT_ENROLL_TOKEN at $TOKEN_FILE"
fi

touch "$COMPOSE_ENV"
upsert_env() {
  local key="$1"
  local val="$2"
  if grep -q "^${key}=" "$COMPOSE_ENV" 2>/dev/null; then
    sed -i.bak "s|^${key}=.*|${key}=${val}|" "$COMPOSE_ENV" && rm -f "${COMPOSE_ENV}.bak"
  else
    echo "${key}=${val}" >>"$COMPOSE_ENV"
  fi
}

upsert_env "TRUSTEDGE_AGENT_ENROLL_TOKEN" "$TRUSTEDGE_AGENT_ENROLL_TOKEN"

# Wire Agent-API → TrustEdge agents upsert (compose defaults to http://backend:8000).
BACKEND_URL="${TRUSTEDGE_BACKEND_URL:-http://backend:8000}"
upsert_env "TRUSTEDGE_BACKEND_URL" "$BACKEND_URL"
if [ -f /etc/trustedge/backend.env ]; then
  TRUSTEDGE_INGEST_TOKEN="$(sudo grep -E '^TRUSTEDGE_INGEST_TOKEN=' /etc/trustedge/backend.env | head -1 | cut -d= -f2- | tr -d '\r' || true)"
  if [ -z "${TRUSTEDGE_INGEST_TOKEN:-}" ]; then
    TRUSTEDGE_INGEST_TOKEN="$(sudo grep -E '^DNS_INGEST_TOKEN=' /etc/trustedge/backend.env | head -1 | cut -d= -f2- | tr -d '\r' || true)"
  fi
  if [ -n "${TRUSTEDGE_INGEST_TOKEN:-}" ]; then
    upsert_env "TRUSTEDGE_INGEST_TOKEN" "$TRUSTEDGE_INGEST_TOKEN"
    echo "Synced TRUSTEDGE_INGEST_TOKEN into ${COMPOSE_ENV} for agent registry upsert"
  fi
fi
# Drop obsolete compose key
if grep -q "^DNS_INGEST_TOKEN=" "$COMPOSE_ENV" 2>/dev/null; then
  sed -i.bak '/^DNS_INGEST_TOKEN=/d' "$COMPOSE_ENV" && rm -f "${COMPOSE_ENV}.bak"
fi

API_IMAGE="${TRUSTEDGE_AGENT_API_IMAGE:-${TRUSTTWIN_API_IMAGE:-}}"
if [ -n "$API_IMAGE" ]; then
  upsert_env "TRUSTEDGE_AGENT_API_IMAGE" "$API_IMAGE"
  echo "Set TRUSTEDGE_AGENT_API_IMAGE in ${COMPOSE_ENV}"
else
  if grep -q "^TRUSTEDGE_AGENT_API_IMAGE=" "$COMPOSE_ENV" 2>/dev/null; then
    sed -i.bak '/^TRUSTEDGE_AGENT_API_IMAGE=/d' "$COMPOSE_ENV" && rm -f "${COMPOSE_ENV}.bak"
    echo "Cleared TRUSTEDGE_AGENT_API_IMAGE from ${COMPOSE_ENV}"
  fi
fi

# Remove legacy compose keys
for legacy in TRUSTTWIN_ENROLL_TOKEN TRUSTTWIN_API_IMAGE; do
  if grep -q "^${legacy}=" "$COMPOSE_ENV" 2>/dev/null; then
    sed -i.bak "/^${legacy}=/d" "$COMPOSE_ENV" && rm -f "${COMPOSE_ENV}.bak"
  fi
done

chmod 600 "$COMPOSE_ENV" 2>/dev/null || true
echo "Synced TrustEdge Agent keys in ${COMPOSE_ENV}"
