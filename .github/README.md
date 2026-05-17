# GitHub Actions CI/CD

This repo now includes `.github/workflows/ci-cd.yml`.

## Trigger model

- `pull_request`: runs CI only
- `push` to `main`: runs CI, then deploys to Azure Container Apps
- `workflow_dispatch`: allows a manual run from GitHub Actions

## GitHub secrets required

- `AZURE_CREDENTIALS`
- `DATABASE_PASSWORD`
- `DOCUMENT_INTELLIGENCE_KEY`
- `AZURE_OPENAI_KEY`
- `TAVILY_API_KEY`
- `OPIK_API_KEY`
- `AUTH_SESSION_SECRET`

Optional secrets:

- `GOOGLE_CLIENT_SECRET`

## GitHub variables required

- `DATABASE_HOST`
- `DATABASE_PORT`
- `DATABASE_NAME`
- `DATABASE_USER`
- `DOCUMENT_INTELLIGENCE_ENDPOINT`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_VERSION`
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`
- `OPIK_WORKSPACE`
- `OPIK_PROJECT_NAME`
- `OPIK_URL_OVERRIDE`

Optional variables:

- `GOOGLE_CLIENT_ID`

## Azure credentials

`AZURE_CREDENTIALS` should contain a service principal JSON payload usable by `azure/login`. The principal needs access to resource group `feb26batch-e2e-project` and permission to manage:

- Azure Container Registry `marketanalystfeb26acr`
- Azure Container Apps environment `marketanalystfeb26-env`
- Azure Container App `marketanalystfeb26`

## Deploy path

The deploy job reuses `scripts/deploy-azure-container-app.ps1`, builds the image in ACR, and updates the live Container App revision.
