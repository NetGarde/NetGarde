#!/usr/bin/env bash
# Resolve trustedge-agent-api ECR image tag (develop → latest fallback) and pull if available.
# Source from deploy; sets TRUSTEDGE_AGENT_API_IMAGE and TRUSTEDGE_AGENT_COMPOSE_PROFILE.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "Source this script from deploy-backend.yml, do not run directly." >&2
  exit 1
fi

set -euo pipefail

ECR_REGISTRY="${ECR_REGISTRY:-804012660077.dkr.ecr.us-east-1.amazonaws.com}"
AGENT_ECR_REPOSITORY="${TRUSTEDGE_AGENT_ECR_REPOSITORY:-trustedge-agent-api}"
LEGACY_ECR_REPOSITORY="${TRUSTTWIN_ECR_REPOSITORY:-trustedge-trusttwin-api}"
BRANCH="${TRUSTEDGE_AGENT_IMAGE_BRANCH:-${TRUSTTWIN_IMAGE_BRANCH:-develop}}"

export TRUSTEDGE_AGENT_COMPOSE_PROFILE=""
export TRUSTEDGE_AGENT_API_IMAGE=""

ecr_tag_exists() {
  local repo="$1"
  local tag="$2"
  aws ecr describe-images \
    --repository-name "$repo" \
    --region "${AWS_REGION:-us-east-1}" \
    --image-ids "imageTag=${tag}" \
    --output json >/dev/null 2>&1
}

pick_tag() {
  local repo="$1"
  if [ "$BRANCH" == "develop" ]; then
    if ecr_tag_exists "$repo" develop; then
      echo develop
      return
    fi
    echo "WARNING: ECR tag :develop not found for ${repo}; trying :latest" >&2
  fi
  if ecr_tag_exists "$repo" latest; then
    echo latest
    return
  fi
  echo ""
}

for repo in "$AGENT_ECR_REPOSITORY" "$LEGACY_ECR_REPOSITORY"; do
  tag="$(pick_tag "$repo")"
  if [ -n "$tag" ]; then
    export TRUSTEDGE_AGENT_API_IMAGE="${ECR_REGISTRY}/${repo}:${tag}"
    echo "Using TRUSTEDGE_AGENT_API_IMAGE=${TRUSTEDGE_AGENT_API_IMAGE}"
    if docker pull "$TRUSTEDGE_AGENT_API_IMAGE"; then
      export TRUSTEDGE_AGENT_COMPOSE_PROFILE="agent"
      echo "trustedge-agent-api image pulled; will start with COMPOSE_PROFILES=agent"
    else
      echo "WARNING: docker pull failed for ${TRUSTEDGE_AGENT_API_IMAGE}; skipping trustedge-agent-api" >&2
      export TRUSTEDGE_AGENT_API_IMAGE=""
    fi
    return 0
  fi
done

echo "WARNING: No trustedge-agent-api image in ECR (${AGENT_ECR_REPOSITORY} or ${LEGACY_ECR_REPOSITORY}). Skipping trustedge-agent-api." >&2
echo "Push TrustEdgeOrg/TrustTwin (develop/main) after setting AWS_ROLE_ARN secret." >&2
return 0
