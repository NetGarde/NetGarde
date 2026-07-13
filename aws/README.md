# AWS scripts

Bash helpers in this folder provision or update AWS resources used by TrustEdge CI/CD (S3, ECR, CloudFront, IAM for GitHub Actions). They are optional, local tooling—not the main application runtime.

Configuration values are read from `aws/.env`; see `.env.example` for the variable names.

## One-command CI setup (TrustEdge rebrand)

After copying and editing `aws/.env` (at minimum `GITHUB_ACTIONS_ROLE_NAME` and `GITHUB_ACTIONS_POLICY_NAME`):

```bash
bash aws/setup-trustedge-ci.sh
```

This runs, in order:

1. **`s3-setup.sh`** — create `trustedge-frontend` S3 bucket + static website hosting
2. **`ecr-setup.sh`** — create `trustedge-backend` ECR repository
3. **`update-github-actions-role.sh`** — IAM policy for GitHub Actions (ECR, S3, CloudFront invalidation)
4. **`cloudfront-frontend-update-origin.sh`** — point CloudFront at the new S3 website origin

**Prerequisites:** AWS CLI authenticated with admin (or equivalent) permissions, `jq` installed.

Then re-run the **Build and Deploy Frontend** and **Build and Deploy Backend** GitHub Actions workflows.

### CI auto-provision (after IAM update)

Deploy workflows automatically create the S3 bucket and ECR repository if missing (`aws/ensure-frontend-bucket.sh`, `aws/ensure-ecr-repo.sh`). Run `update-github-actions-role.sh` once locally so the GitHub Actions role includes create permissions.

CloudFront origin update still requires one local run of `setup-trustedge-ci.sh` (or `cloudfront-frontend-update-origin.sh` only).

### TrustEdge Agent API (separate repo)

`TrustEdgeOrg/TrustEdge-Agent` uses the same OIDC role to push `trustedge-agent-api` to ECR.

1. Run **`update-github-actions-trust-policy.sh`** once (adds `TrustEdgeOrg/TrustEdge-Agent` to the role trust policy).
2. In the TrustEdge-Agent repo, set GitHub secret **`AWS_ROLE_ARN`** to the same ARN as TrustEdge (e.g. `arn:aws:iam::804012660077:role/GitHubActionsDeployRole`).
3. Push to `develop` or run the **Build and Deploy trustedge-agent-api** workflow.

See `TrustEdge-Agent/aws/README.md` for details.

## Individual scripts

### `s3-setup.sh`

Creates the frontend S3 bucket if it does not already exist, then turns on static website hosting (`index.html` for both index and error document), applies a public read bucket policy, relaxes the bucket public-access block so that policy can take effect, and sets a permissive CORS rule for GET/HEAD. Prints the S3 website endpoint when finished.

### `ecr-setup.sh`

Creates the backend ECR repository (`ECR_REPOSITORY`, default `trustedge-backend`) if it does not exist.

### `cloudfront-frontend-update-origin.sh`

Updates the configured CloudFront distribution so its frontend origin domain matches `FRONTEND_S3_BUCKET` (S3 website endpoint). Idempotent.

### `cloudfront-backend-setup.sh`

Builds a CloudFront distribution config with an HTTP custom origin to the EC2 public DNS name and backend port from the environment file, HTTPS for viewers, query strings and cookies forwarded, cache TTLs set to zero for the default behavior, and all common HTTP methods allowed. Creates the distribution via the AWS CLI and prints the new distribution id and domain.

### `update-github-actions-role.sh`

Replaces or creates an inline IAM policy on the configured GitHub Actions role: ECR image push/pull actions, list/read/write/delete objects for the frontend S3 bucket, and CloudFront invalidation APIs. Intended for an OIDC-based deploy role used by CI.

### `update-github-actions-trust-policy.sh`

Updates the role **trust policy** so additional GitHub repos (e.g. `TrustEdgeOrg/TrustEdge-Agent`) can assume the deploy role via OIDC. Run after adding a new repo that needs ECR/S3 deploy access.
