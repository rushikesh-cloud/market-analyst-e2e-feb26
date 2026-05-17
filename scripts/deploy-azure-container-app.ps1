param(
    [string]$ResourceGroup = "feb26batch-e2e-project",
    [string]$Location = "westus2",
    [string]$ContainerAppName = "marketanalystfeb26",
    [string]$ContainerEnvName = "marketanalystfeb26-env",
    [string]$AcrName = "marketanalystfeb26acr",
    [string]$ImageTag = "",
    [string]$SubscriptionId = ""
)

$ErrorActionPreference = "Stop"

function Set-EnvFromDotEnv {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return
    }

    foreach ($rawLine in Get-Content $Path) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            continue
        }

        $parts = $line.Split("=", 2)
        $key = $parts[0].Trim()
        $value = $parts[1].Trim().Trim("'").Trim('"')
        if ($key) {
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

function Add-PlainEnvVar {
    param(
        [System.Collections.Generic.List[string]]$List,
        [string]$Name,
        [string]$Value,
        [switch]$AllowEmpty
    )

    if ($AllowEmpty -or -not [string]::IsNullOrWhiteSpace($Value)) {
        $List.Add("${Name}=${Value}")
    }
}

function Add-Secret {
    param(
        [System.Collections.Generic.List[string]]$SecretList,
        [System.Collections.Generic.List[string]]$EnvVarList,
        [string]$SecretName,
        [string]$EnvName,
        [string]$SecretValue
    )

    if ([string]::IsNullOrWhiteSpace($SecretValue)) {
        return
    }

    $SecretList.Add("${SecretName}=${SecretValue}")
    $EnvVarList.Add("${EnvName}=secretref:${SecretName}")
}

function Get-AzOptionalValue {
    param([string[]]$Arguments)

    $output = & az @Arguments 2>$null
    if ($LASTEXITCODE -ne 0) {
        return ""
    }

    return ($output | Out-String).Trim()
}

function New-EnvVarList {
    param(
        [string]$FrontendUrl,
        [System.Collections.Generic.List[string]]$SecretList,
        [string]$AuthSessionSecret
    )

    $envVars = [System.Collections.Generic.List[string]]::new()

    Add-PlainEnvVar $envVars "DATABASE_HOST" $env:DATABASE_HOST
    Add-PlainEnvVar $envVars "DATABASE_PORT" $env:DATABASE_PORT
    Add-PlainEnvVar $envVars "DATABASE_NAME" $env:DATABASE_NAME
    Add-PlainEnvVar $envVars "DATABASE_USER" $env:DATABASE_USER
    Add-PlainEnvVar $envVars "DOCUMENT_INTELLIGENCE_ENDPOINT" $env:DOCUMENT_INTELLIGENCE_ENDPOINT
    Add-PlainEnvVar $envVars "AZURE_OPENAI_ENDPOINT" $env:AZURE_OPENAI_ENDPOINT
    Add-PlainEnvVar $envVars "AZURE_OPENAI_DEPLOYMENT" $env:AZURE_OPENAI_DEPLOYMENT
    Add-PlainEnvVar $envVars "AZURE_OPENAI_VERSION" $env:AZURE_OPENAI_VERSION
    Add-PlainEnvVar $envVars "AZURE_OPENAI_EMBEDDING_DEPLOYMENT" $env:AZURE_OPENAI_EMBEDDING_DEPLOYMENT
    Add-PlainEnvVar $envVars "OPIK_WORKSPACE" $env:OPIK_WORKSPACE
    Add-PlainEnvVar $envVars "OPIK_PROJECT_NAME" $env:OPIK_PROJECT_NAME
    Add-PlainEnvVar $envVars "OPIK_URL_OVERRIDE" $env:OPIK_URL_OVERRIDE
    Add-PlainEnvVar $envVars "FRONTEND_APP_URL" $FrontendUrl
    Add-PlainEnvVar $envVars "AUTH_COOKIE_SECURE" "true"
    Add-PlainEnvVar $envVars "CORS_ORIGINS" $FrontendUrl

    Add-Secret $SecretList $envVars "database-password" "DATABASE_PASSWORD" $env:DATABASE_PASSWORD
    Add-Secret $SecretList $envVars "document-intelligence-key" "DOCUMENT_INTELLIGENCE_KEY" $env:DOCUMENT_INTELLIGENCE_KEY
    Add-Secret $SecretList $envVars "azure-openai-key" "AZURE_OPENAI_KEY" $env:AZURE_OPENAI_KEY
    Add-Secret $SecretList $envVars "tavily-api-key" "TAVILY_API_KEY" $env:TAVILY_API_KEY
    Add-Secret $SecretList $envVars "opik-api-key" "OPIK_API_KEY" $env:OPIK_API_KEY
    Add-Secret $SecretList $envVars "auth-session-secret" "AUTH_SESSION_SECRET" $AuthSessionSecret

    if (-not [string]::IsNullOrWhiteSpace($env:GOOGLE_CLIENT_ID) -and -not [string]::IsNullOrWhiteSpace($env:GOOGLE_CLIENT_SECRET)) {
        Add-PlainEnvVar $envVars "GOOGLE_CLIENT_ID" $env:GOOGLE_CLIENT_ID
        Add-Secret $SecretList $envVars "google-client-secret" "GOOGLE_CLIENT_SECRET" $env:GOOGLE_CLIENT_SECRET
        Add-PlainEnvVar $envVars "GOOGLE_OAUTH_REDIRECT_URI" "$FrontendUrl/api/auth/google/callback"
    }

    return $envVars
}

if (-not $ImageTag) {
    $ImageTag = Get-Date -Format "yyyyMMdd-HHmmss"
}

if ($SubscriptionId) {
    az account set --subscription $SubscriptionId | Out-Null
}

$defaultCaBundle = "C:\temp\azcli-ca-bundle.pem"
if (-not $env:REQUESTS_CA_BUNDLE -and (Test-Path $defaultCaBundle)) {
    $env:REQUESTS_CA_BUNDLE = $defaultCaBundle
}
if (-not $env:SSL_CERT_FILE -and -not [string]::IsNullOrWhiteSpace($env:REQUESTS_CA_BUNDLE)) {
    $env:SSL_CERT_FILE = $env:REQUESTS_CA_BUNDLE
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-EnvFromDotEnv -Path (Join-Path $repoRoot ".env")

$imageName = "$AcrName.azurecr.io/market-analyst:$ImageTag"
$frontendUrl = "https://placeholder.invalid"
$authSessionSecret = if (-not [string]::IsNullOrWhiteSpace($env:AUTH_SESSION_SECRET)) {
    $env:AUTH_SESSION_SECRET
} else {
    [Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }))
}

Write-Host "Ensuring Container Apps extension..."
az extension add --name containerapp --upgrade | Out-Null

Write-Host "Ensuring ACR $AcrName..."
$acrExists = Get-AzOptionalValue @("acr", "show", "-n", $AcrName, "-g", $ResourceGroup, "--query", "name", "-o", "tsv")
if (-not $acrExists) {
    az acr create -n $AcrName -g $ResourceGroup --sku Basic --admin-enabled true --location $Location | Out-Null
}

Write-Host "Ensuring ACA environment $ContainerEnvName..."
$envExists = Get-AzOptionalValue @("containerapp", "env", "show", "-n", $ContainerEnvName, "-g", $ResourceGroup, "--query", "name", "-o", "tsv")
if (-not $envExists) {
    az containerapp env create -n $ContainerEnvName -g $ResourceGroup -l $Location | Out-Null
}

Write-Host "Building image $imageName..."
az acr build --registry $AcrName --image "market-analyst:$ImageTag" $repoRoot

$initialSecrets = [System.Collections.Generic.List[string]]::new()
$initialEnvVars = New-EnvVarList -FrontendUrl $frontendUrl -SecretList $initialSecrets -AuthSessionSecret $authSessionSecret

Write-Host "Creating or updating container app $ContainerAppName..."
$existingApp = Get-AzOptionalValue @("containerapp", "show", "-n", $ContainerAppName, "-g", $ResourceGroup, "--query", "name", "-o", "tsv")
if (-not $existingApp) {
    az containerapp create `
        -n $ContainerAppName `
        -g $ResourceGroup `
        --environment $ContainerEnvName `
        --image $imageName `
        --target-port 8080 `
        --ingress external `
        --system-assigned `
        --cpu 2.0 `
        --memory 4Gi `
        --min-replicas 1 `
        --max-replicas 1 `
        --secrets $initialSecrets `
        --env-vars $initialEnvVars | Out-Null
} else {
    az containerapp identity assign -n $ContainerAppName -g $ResourceGroup --system-assigned | Out-Null
    az containerapp update `
        -n $ContainerAppName `
        -g $ResourceGroup `
        --image $imageName `
        --replace-env-vars $initialEnvVars `
        --secrets $initialSecrets | Out-Null
}

$principalId = az containerapp show -n $ContainerAppName -g $ResourceGroup --query "identity.principalId" -o tsv
$acrId = az acr show -n $AcrName -g $ResourceGroup --query "id" -o tsv

Write-Host "Assigning AcrPull..."
az role assignment create --assignee-object-id $principalId --assignee-principal-type ServicePrincipal --role AcrPull --scope $acrId 2>$null | Out-Null

Write-Host "Configuring registry identity..."
az containerapp registry set -n $ContainerAppName -g $ResourceGroup --server "$AcrName.azurecr.io" --identity system | Out-Null
az containerapp update -n $ContainerAppName -g $ResourceGroup --image $imageName | Out-Null

$fqdn = az containerapp show -n $ContainerAppName -g $ResourceGroup --query "properties.configuration.ingress.fqdn" -o tsv
$frontendUrl = "https://$fqdn"

$finalSecrets = [System.Collections.Generic.List[string]]::new()
$finalEnvVars = New-EnvVarList -FrontendUrl $frontendUrl -SecretList $finalSecrets -AuthSessionSecret $authSessionSecret

Write-Host "Updating public URL-dependent settings..."
az containerapp update -n $ContainerAppName -g $ResourceGroup --replace-env-vars $finalEnvVars --secrets $finalSecrets | Out-Null

Write-Host ""
Write-Host "Deployment complete"
Write-Host "Image: $imageName"
Write-Host "URL:   $frontendUrl"
