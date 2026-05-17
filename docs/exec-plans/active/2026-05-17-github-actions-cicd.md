# GitHub Actions CI/CD

## Goal

Add a repo-native GitHub Actions pipeline that validates the current frontend/backend surfaces on every GitHub push or pull request and deploys the Azure Container Apps workload on pushes to `main`.

## Scope

- Add a single workflow under `.github/workflows/`.
- Keep CI focused on the currently stable auth/backend tests plus frontend lint/build.
- Reuse the existing Azure deployment script instead of duplicating ACA logic in YAML.
- Move deploy-time secrets and stable config into GitHub Actions secrets/variables rather than relying on the local `.env` file.
- Keep the deploy target fixed to resource group `feb26batch-e2e-project`.

## Verification

- Validate the workflow YAML structure locally.
- Run the same CI commands locally where practical.
- Keep the deploy script compatible with CI-provided `AUTH_SESSION_SECRET` so sessions remain stable across deployments.
