#!/usr/bin/env bash
# Legacy wrapper — use scripts/ec2-sync-agent-api.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/ec2-sync-agent-api.sh" "$@"
