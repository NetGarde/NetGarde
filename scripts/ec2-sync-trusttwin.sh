#!/usr/bin/env bash
# Ensure TrustTwin ingest token + compose env for trusttwin-api container.
set -euo pipefail

REPO_ROOT="${TRUSTEDGE_REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
COMPOSE_ENV="${REPO_ROOT}/.env"
TOKEN_FILE="/etc/trustedge/trusttwin-enroll.token"

sudo mkdir -p /etc/trustedge

if sudo test -f "$TOKEN_FILE"; then
  TRUSTTWIN_ENROLL_TOKEN="$(sudo cat "$TOKEN_FILE" | tr -d '\r\n')"
  echo "Loaded TRUSTTWIN_ENROLL_TOKEN from $TOKEN_FILE"
else
  TRUSTTWIN_ENROLL_TOKEN="$(openssl rand -hex 32)"
  echo "$TRUSTTWIN_ENROLL_TOKEN" | sudo tee "$TOKEN_FILE" >/dev/null
  if getent group docker >/dev/null 2>&1; then
    sudo chown root:docker "$TOKEN_FILE"
    sudo chmod 640 "$TOKEN_FILE"
  else
    sudo chmod 600 "$TOKEN_FILE"
  fi
  echo "Generated TRUSTTWIN_ENROLL_TOKEN at $TOKEN_FILE"
fi

touch "$COMPOSE_ENV"
for kv in "TRUSTTWIN_ENROLL_TOKEN=${TRUSTTWIN_ENROLL_TOKEN}" "TRUSTTWIN_BUILD_CONTEXT=${TRUSTTWIN_BUILD_CONTEXT:-$HOME/TrustTwin}"; do
  key="${kv%%=*}"
  if grep -q "^${key}=" "$COMPOSE_ENV" 2>/dev/null; then
    sed -i.bak "s|^${key}=.*|${kv}|" "$COMPOSE_ENV" && rm -f "${COMPOSE_ENV}.bak"
  else
    echo "$kv" >>"$COMPOSE_ENV"
  fi
done
chmod 600 "$COMPOSE_ENV" 2>/dev/null || true
echo "Synced TrustTwin keys in ${COMPOSE_ENV}"
