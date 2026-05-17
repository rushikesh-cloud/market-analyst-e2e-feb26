# Azure Container Apps Deployment

## Goal

Package the current Next.js frontend and FastAPI backend into one production container, front it with nginx inside the same image, and deploy that container to Azure Container Apps in resource group `feb26batch-e2e-project`.

## Scope

- Keep the deploy surface single-container for this slice.
- Route browser traffic through nginx so `/api/*` reaches FastAPI and all non-API routes reach the Next.js app.
- Make the frontend default to same-origin API calls so the public app only needs one ACA ingress endpoint.
- Support HTTPS-safe auth cookies in deployed environments.
- Add a repeatable Azure CLI deployment script for building, pushing, and updating the ACA app.

## Verification

- Run targeted frontend lint if the touched frontend surface permits it.
- Build the Docker image locally.
- Use Azure CLI to create or reuse the ACA environment, ACR, and app resources inside `feb26batch-e2e-project`.
- Verify the deployed app ingress plus `/health`.
