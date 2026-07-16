#!/usr/bin/env bash
# Push ADMIN_API_TOKEN / TRUSTEDGE_INGEST_TOKEN from backend.env into compose .env
set -euo pipefail

ENV_FILE="${TRUSTEDGE_ENV_FILE:-/etc/trustedge/backend.env}"
REPO_ROOT="${TRUSTEDGE_REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
COMPOSE_ENV="${REPO_ROOT}/.env"

read_env() {
  local key="$1"
  sudo grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- || true
}

if ! sudo test -f "$ENV_FILE"; then
  echo "Missing $ENV_FILE — run ec2-sync-backend-env.sh first" >&2
  exit 1
fi

TRUSTEDGE_INGEST_TOKEN="$(read_env TRUSTEDGE_INGEST_TOKEN)"
# Legacy fallback during rollout
if [ -z "$TRUSTEDGE_INGEST_TOKEN" ]; then
  TRUSTEDGE_INGEST_TOKEN="$(read_env DNS_INGEST_TOKEN)"
fi
ADMIN_API_TOKEN="$(read_env ADMIN_API_TOKEN)"

touch "$COMPOSE_ENV"
upsert_env() {
  local key="$1"
  local val="$2"
  [ -n "$val" ] || return 0
  if grep -q "^${key}=" "$COMPOSE_ENV" 2>/dev/null; then
    sed -i.bak "s|^${key}=.*|${key}=${val}|" "$COMPOSE_ENV" && rm -f "${COMPOSE_ENV}.bak"
  else
    echo "${key}=${val}" >>"$COMPOSE_ENV"
  fi
}

upsert_env "TRUSTEDGE_INGEST_TOKEN" "$TRUSTEDGE_INGEST_TOKEN"
upsert_env "ADMIN_API_TOKEN" "$ADMIN_API_TOKEN"

# Drop obsolete compose keys from removed DNS/VPN host services
for legacy in DNS_INGEST_TOKEN BLOCK_PAGE_IP BLOCK_IP BLOCK_IPV6_IP; do
  if grep -q "^${legacy}=" "$COMPOSE_ENV" 2>/dev/null; then
    sed -i.bak "/^${legacy}=/d" "$COMPOSE_ENV" && rm -f "${COMPOSE_ENV}.bak"
  fi
done

chmod 600 "$COMPOSE_ENV" 2>/dev/null || true
echo "Updated ${COMPOSE_ENV} (TRUSTEDGE_INGEST_TOKEN + ADMIN_API_TOKEN)"
