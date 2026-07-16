#!/usr/bin/env bash
# Push ADMIN_API_TOKEN / DNS_INGEST_TOKEN from backend.env into host services + compose .env
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

DNS_INGEST_TOKEN="$(read_env DNS_INGEST_TOKEN)"
ADMIN_API_TOKEN="$(read_env ADMIN_API_TOKEN)"
BLOCK_PAGE_IP="$(read_env BLOCK_PAGE_IP)"
BLOCK_IP="$(read_env BLOCK_IP)"
BLOCK_IPV6_IP="$(read_env BLOCK_IPV6_IP)"
if [ -z "$BLOCK_IP" ]; then
  BLOCK_IP="${BLOCK_PAGE_IP:-10.0.0.1}"
fi
if [ -z "$BLOCK_IPV6_IP" ]; then
  BLOCK_IPV6_IP="::"
fi

# --- trustedge-log-watcher (DNS → POST /dns-queries/bulk) ---
if systemctl list-unit-files trustedge-log-watcher.service >/dev/null 2>&1; then
  sudo mkdir -p /etc/systemd/system/trustedge-log-watcher.service.d
  if [ -n "$DNS_INGEST_TOKEN" ]; then
    printf '%s\n' "[Service]" "Environment=DNS_INGEST_TOKEN=${DNS_INGEST_TOKEN}" | \
      sudo tee /etc/systemd/system/trustedge-log-watcher.service.d/tokens.conf >/dev/null
    echo "Updated trustedge-log-watcher DNS_INGEST_TOKEN"
  else
    sudo rm -f /etc/systemd/system/trustedge-log-watcher.service.d/tokens.conf
    echo "WARNING: DNS_INGEST_TOKEN empty — log watcher may get 401 on ingest"
  fi
  sudo systemctl daemon-reload
  sudo systemctl restart trustedge-log-watcher || true
fi

# --- repo-root .env for docker compose (dns-sync needs both tokens) ---
touch "$COMPOSE_ENV"
for key in DNS_INGEST_TOKEN ADMIN_API_TOKEN; do
  val="$(read_env "$key")"
  [ -n "$val" ] || continue
  if grep -q "^${key}=" "$COMPOSE_ENV" 2>/dev/null; then
    sed -i.bak "s|^${key}=.*|${key}=${val}|" "$COMPOSE_ENV" && rm -f "${COMPOSE_ENV}.bak"
  else
    echo "${key}=${val}" >>"$COMPOSE_ENV"
  fi
done
for kv in "BLOCK_PAGE_IP=${BLOCK_PAGE_IP:-10.0.0.1}" "BLOCK_IP=${BLOCK_IP}" "BLOCK_IPV6_IP=${BLOCK_IPV6_IP:-::}"; do
  key="${kv%%=*}"
  if grep -q "^${key}=" "$COMPOSE_ENV" 2>/dev/null; then
    sed -i.bak "s|^${key}=.*|${kv}|" "$COMPOSE_ENV" && rm -f "${COMPOSE_ENV}.bak"
  else
    echo "$kv" >>"$COMPOSE_ENV"
  fi
done
chmod 600 "$COMPOSE_ENV" 2>/dev/null || true
echo "Updated ${COMPOSE_ENV} (BLOCK_IP=${BLOCK_IP})"
