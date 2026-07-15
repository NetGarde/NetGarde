#!/usr/bin/env bash
# Install and configure CloudWatch Agent for TrustEdge EC2 (Docker + systemd logs).
# Requires EC2 instance IAM role with logs:CreateLogGroup, PutLogEvents, etc.
#
# Run on the host after deploy:
#   sudo bash scripts/ec2-setup-cloudwatch.sh
#
# Optional env:
#   AWS_REGION=us-east-1
#   TRUSTEDGE_ENV_FILE=/etc/trustedge/backend.env
set -euo pipefail

REPO_ROOT="${TRUSTEDGE_REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$REPO_ROOT"

AWS_REGION="${AWS_REGION:-us-east-1}"
ENV_FILE="${TRUSTEDGE_ENV_FILE:-/etc/trustedge/backend.env}"
AGENT_CONFIG_SRC="${REPO_ROOT}/scripts/cloudwatch/amazon-cloudwatch-agent.json"
AGENT_CONFIG_DST="/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json"

echo "Installing Amazon CloudWatch Agent (region=${AWS_REGION})..."
if ! command -v amazon-cloudwatch-agent-ctl >/dev/null 2>&1; then
  CW_DEB="/tmp/amazon-cloudwatch-agent.deb"
  curl -fsSL -o "$CW_DEB" \
    "https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb"
  sudo dpkg -i -E "$CW_DEB"
  rm -f "$CW_DEB"
fi

echo "Installing CloudWatch Agent config..."
sudo mkdir -p "$(dirname "$AGENT_CONFIG_DST")"
sudo cp "$AGENT_CONFIG_SRC" "$AGENT_CONFIG_DST"

set_env_kv() {
  local key="$1" value="$2"
  if sudo grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sudo sed -i.bak "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
    sudo rm -f "${ENV_FILE}.bak"
  else
    echo "${key}=${value}" | sudo tee -a "$ENV_FILE" >/dev/null
  fi
}

echo "Enabling structured JSON logs in ${ENV_FILE}..."
set_env_kv LOG_JSON 1
set_env_kv LOG_LEVEL INFO
set_env_kv LOG_TO_FILE 0
set_env_kv LOG_SERVICE backend

echo "Ensuring fixed Docker container name for dns-sync..."
if ! grep -q 'container_name: trustedge-dns-sync' docker-compose.yml; then
  echo "WARNING: trustedge-dns-sync container_name missing from docker-compose.yml; update repo and redeploy"
fi

echo "Starting CloudWatch Agent..."
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -c "file:${AGENT_CONFIG_DST}" \
  -s

echo "Applying log group retention policies..."
for spec in "/trustedge/prod/backend:30" "/trustedge/prod/dns-sync:14" "/trustedge/prod/detection-engine:14" "/trustedge/prod/log-watcher:14" "/trustedge/prod/wg-agent:14"; do
  group="${spec%%:*}"
  days="${spec##*:}"
  aws logs create-log-group --log-group-name "$group" --region "$AWS_REGION" 2>/dev/null || true
  aws logs put-retention-policy --log-group-name "$group" --retention-in-days "$days" --region "$AWS_REGION" || true
done

echo "Recreating backend to pick up LOG_JSON (if running)..."
docker compose -f docker-compose.yml up -d --force-recreate backend 2>/dev/null || true

echo "CloudWatch logging enabled."
echo "  Log groups: /trustedge/prod/backend (30d), dns-sync (14d), detection-engine (14d), log-watcher (14d), wg-agent (14d)"
echo "  Example query (Logs Insights): fields @timestamp, level, event, message | filter level = \"ERROR\""
