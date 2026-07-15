#!/usr/bin/env bash
# Legacy wrapper — source scripts/ec2-resolve-agent-api.sh instead.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "Source scripts/ec2-resolve-agent-api.sh from deploy, do not run directly." >&2
  exit 1
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/ec2-resolve-agent-api.sh"
