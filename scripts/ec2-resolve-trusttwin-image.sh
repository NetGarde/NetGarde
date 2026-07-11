#!/usr/bin/env bash
# Resolve trusttwin-api ECR image tag (develop → latest fallback) and pull if available.
# Source from deploy; sets TRUSTTWIN_API_IMAGE and TRUSTTWIN_COMPOSE_PROFILE.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "Source this script from deploy-backend.yml, do not run directly." >&2
  exit 1
fi

set -euo pipefail

ECR_REGISTRY="${ECR_REGISTRY:-804012660077.dkr.ecr.us-east-1.amazonaws.com}"
TRUSTTWIN_ECR_REPOSITORY="${TRUSTTWIN_ECR_REPOSITORY:-trustedge-trusttwin-api}"
BRANCH="${TRUSTTWIN_IMAGE_BRANCH:-develop}"

export TRUSTTWIN_COMPOSE_PROFILE=""
export TRUSTTWIN_API_IMAGE=""

ecr_tag_exists() {
  local tag="$1"
  aws ecr describe-images \
    --repository-name "$TRUSTTWIN_ECR_REPOSITORY" \
    --region "${AWS_REGION:-us-east-1}" \
    --image-ids "imageTag=${tag}" \
    --output json >/dev/null 2>&1
}

pick_tag() {
  if [ "$BRANCH" == "develop" ]; then
    if ecr_tag_exists develop; then
      echo develop
      return
    fi
    echo "WARNING: ECR tag :develop not found for ${TRUSTTWIN_ECR_REPOSITORY}; trying :latest" >&2
  fi
  if ecr_tag_exists latest; then
    echo latest
    return
  fi
  echo ""
}

tag="$(pick_tag)"
if [ -z "$tag" ]; then
  echo "WARNING: No trusttwin-api image in ECR (${TRUSTTWIN_ECR_REPOSITORY}:develop or :latest). Skipping trusttwin-api." >&2
  echo "Push TrustEdgeOrg/TrustTwin (develop/main) after setting AWS_ROLE_ARN secret." >&2
  return 0
fi

export TRUSTTWIN_API_IMAGE="${ECR_REGISTRY}/${TRUSTTWIN_ECR_REPOSITORY}:${tag}"
echo "Using TRUSTTWIN_API_IMAGE=${TRUSTTWIN_API_IMAGE}"

if docker pull "$TRUSTTWIN_API_IMAGE"; then
  export TRUSTTWIN_COMPOSE_PROFILE="trusttwin"
  echo "trusttwin-api image pulled; will start with COMPOSE_PROFILES=trusttwin"
else
  echo "WARNING: docker pull failed for ${TRUSTTWIN_API_IMAGE}; skipping trusttwin-api" >&2
  export TRUSTTWIN_API_IMAGE=""
fi
