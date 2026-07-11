#!/bin/bash
# Extend the GitHub Actions OIDC IAM role trust policy for additional repos.
#
# The deploy role is scoped by repo in the trust policy (token.actions.githubusercontent.com:sub).
# TrustTwin CI needs TrustEdgeOrg/TrustTwin in addition to TrustEdgeOrg/TrustEdge.
#
# Usage (from TrustEdge repo root):
#   bash aws/update-github-actions-trust-policy.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "ERROR: $SCRIPT_DIR/.env not found. Copy aws/.env.example to aws/.env and edit values."
    exit 1
fi

set -a
# shellcheck disable=SC1091
source "$SCRIPT_DIR/.env"
set +a

ROLE_NAME="${GITHUB_ACTIONS_ROLE_NAME:?Set GITHUB_ACTIONS_ROLE_NAME in aws/.env}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
OIDC_PROVIDER_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"

# Space-separated GitHub repos allowed to assume the role (org/repo).
GITHUB_OIDC_REPOS="${GITHUB_OIDC_REPOS:-TrustEdgeOrg/TrustEdge TrustEdgeOrg/TrustTwin}"

echo "Updating OIDC trust policy for role: $ROLE_NAME"
echo "Allowed repos: $GITHUB_OIDC_REPOS"
echo ""

subs=()
for repo in $GITHUB_OIDC_REPOS; do
    subs+=("repo:${repo}:*")
done

policy_json="$(jq -n \
    --arg provider "$OIDC_PROVIDER_ARN" \
    --argjson subs "$(printf '%s\n' "${subs[@]}" | jq -R . | jq -s .)" \
    '{
      Version: "2012-10-17",
      Statement: [
        {
          Effect: "Allow",
          Principal: { Federated: $provider },
          Action: "sts:AssumeRoleWithWebIdentity",
          Condition: {
            StringEquals: {
              "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
            },
            StringLike: {
              "token.actions.githubusercontent.com:sub": $subs
            }
          }
        }
      ]
    }')"

aws iam update-assume-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-document "$policy_json"

echo "[OK] Trust policy updated"
echo ""
echo "Add this GitHub Actions secret to each repo that deploys to AWS:"
echo "  AWS_ROLE_ARN=arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"
echo ""
echo "TrustTwin: Settings → Secrets and variables → Actions → New repository secret"
