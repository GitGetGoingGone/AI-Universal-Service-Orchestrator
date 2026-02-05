# Git and Azure CLI Setup

Instructions for connecting Git with Azure, deploying from **Azure DevOps Pipelines**, and configuring App Service. Assumes the repo lives in Azure DevOps.

## Deployment flow (Azure DevOps)

1. **Part 1–2**: Azure CLI + push code to Azure Repos
2. **Part 3**: Create App Service (CLI or Portal)
3. **Part 4**: Create service connection (Azure DevOps → Azure)
4. **Part 5**: Create pipeline + set startup command + app settings
5. Push to `main` → pipeline deploys

---

## Part 1: Azure CLI

### Install

**macOS (Homebrew)**

```bash
brew update && brew install azure-cli
```

**Windows (winget)**

```bash
winget install Microsoft.AzureCLI
```

**Linux**

```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### Login

```bash
az login
```

Opens a browser for interactive sign-in. After success, you'll see your subscriptions.

### Verify

```bash
az account show
az account list --output table
```

### Set default subscription (if you have multiple)

```bash
az account set --subscription "<subscription-id-or-name>"
```

---

## Part 2: Git + Azure DevOps Repos

Azure DevOps has its own Git hosting. To connect your local Git to Azure DevOps:

### 2.1 Create Azure DevOps project and repo

**Option A: Azure Portal**

1. Go to [dev.azure.com](https://dev.azure.com)
2. Create organization (if needed) → New project → Create repository

**Option B: Azure CLI**

```bash
# Install Azure DevOps extension (one-time)
az extension add --name azure-devops

# Configure defaults
az devops configure --defaults organization=https://dev.azure.com/<org> project=<project>

# Create repo (if not exists)
az repos create --name "AI-Universal-Service-Orchestrator" --output table
```

### 2.2 Connect existing local repo to Azure DevOps

```bash
# Add Azure DevOps as remote
az repos list --output table   # get repo URL
git remote add azure https://dev.azure.com/aiuso/aiuso/_git/AI-Universal-Service-Orchestrator

# Or use SSH (recommended)
git remote add azure git@ssh.dev.azure.com:v3/<org>/<project>/<repo-name>
```

### 2.3 Authentication for Azure DevOps Git

**Option A: Personal Access Token (PAT)**

1. Azure DevOps → User settings (top right) → Personal access tokens
2. New token: scope **Code (Read & write)**
3. Copy token

```bash
# When Git prompts for password, use the PAT (not your Azure password)
git push azure main
# Username: <your-email or anything>
# Password: <paste-PAT>
```

**Option B: Git Credential Manager (recommended)**

Git Credential Manager stores credentials securely:

```bash
# macOS - usually installed with Git or Azure CLI
git config --global credential.helper osxkeychain

# Or use Azure DevOps credential helper
git config --global credential.https://dev.azure.com.helper manager
```

First `git push` or `git pull` will prompt for login; credentials are cached.

**Option C: SSH key**

1. Generate key: `ssh-keygen -t ed25519 -C "your@email.com"`
2. Azure DevOps → User settings → SSH public keys → Add
3. Use SSH remote: `git@ssh.dev.azure.com:v3/<org>/<project>/<repo>`

---

## Part 3: Git + Azure App Service (Deploy from CLI)

Deploy your app to Azure App Service using Azure CLI and Git.

### 3.1 Create App Service and enable local Git deployment

```bash
# Variables
RESOURCE_GROUP="AI-USO"
APP_NAME="aiuso"
LOCATION="centralus"

az webapp deployment source show --name $APP_NAME --resource-group $RESOURCE_GROUP --query url -o tsv

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create App Service plan
az appservice plan create --name "${APP_NAME}-plan" --resource-group $RESOURCE_GROUP \
  --sku B1 --is-linux

# Create web app (Python 3.11)
az webapp create --name $APP_NAME --resource-group $RESOURCE_GROUP \
  --plan "${APP_NAME}-plan" --runtime "PYTHON:3.11"

# Enable local Git deployment
az webapp deployment source config-local-git --name $APP_NAME --resource-group $RESOURCE_GROUP
```

### 3.2 Get deployment credentials and Git URL

**Option A: Set subscription-level deployment user (one-time, for all App Service Git deploys)**

```bash
az webapp deployment user set --user-name <your-username> --password <strong-password>
```

**Option B: Get app-specific publishing credentials (use these when pushing)**

```bash
# Get username
az webapp deployment list-publishing-credentials --name $APP_NAME --resource-group $RESOURCE_GROUP --query publishingUserName -o tsv

# Get password
az webapp deployment list-publishing-credentials --name $APP_NAME --resource-group $RESOURCE_GROUP --query publishingPassword -o tsv
```

**Get Git clone URL**

```bash
az webapp deployment source config-local-git --name $APP_NAME --resource-group $RESOURCE_GROUP --query url -o tsv
```


### 3.3 Push to Azure (local Git)

```bash
# Add Azure App Service as remote
GIT_URL=$(az webapp deployment source config-local-git --name $APP_NAME --resource-group $RESOURCE_GROUP --query url -o tsv)
git remote add azure-app $GIT_URL

# Deploy
git push azure-app main
```

You'll be prompted for deployment username/password (from step 3.2).

---

## Part 4: Azure DevOps Service Connection

The pipeline needs a **service connection** to deploy to Azure. Create it in Azure DevOps.

### 4.1 Automatic creation (recommended)

1. **Azure DevOps** → Project → **Project Settings** → **Service connections** → **New service connection**
2. Choose **Azure Resource Manager** → **Next**
3. **Identity type**: App registration (automatic)
4. **Credential**: Select **Secret** (not Workload identity federation – often fixes resource group loading)
5. **Scope level**: Subscription
6. **Subscription**: Select your subscription
7. **Resource group**: Optional – leave empty if it doesn’t load; pipeline can still deploy
8. **Grant access permission to all pipelines**: Check if you want all pipelines to use it
9. **Verify** → **Save**

### 4.2 Manual creation (if automatic fails)

If you get "Failed to obtain JWT" or resource group won’t load:

**Step 1: Create app registration (Azure Portal or CLI)**

```bash
# Azure CLI
APP_ID=$(az ad app create --display-name "azure-devops-aiuso" --query appId -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
az ad sp create --id $APP_ID
SECRET=$(az ad app credential reset --id $APP_ID --years 2 --query password -o tsv)

echo "Client ID: $APP_ID"
echo "Tenant ID: $TENANT_ID"
echo "Client Secret: $SECRET"
```

**Step 2: Grant Contributor role**

```bash
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
az role assignment create --assignee $APP_ID --role Contributor --scope /subscriptions/$SUBSCRIPTION_ID
```

**Step 3: Create service connection manually**

1. Service connections → **New** → **Azure Resource Manager**
2. Click **create manually**
3. Enter:
   - **Subscription ID**, **Subscription Name**
   - **Service Principal ID** = Client ID from step 1
   - **Service Principal Key** = Client secret value (not Secret ID)
   - **Tenant ID** from step 1
4. **Verify** → **Save**

### 4.3 Troubleshooting service connections

| Issue | Fix |
|-------|-----|
| Resource group not loading | Use **Credential: Secret** instead of Workload identity federation |
| Failed to obtain JWT | Verify Client ID, Tenant ID, Secret; ensure role assignment exists |
| Secret expired | Create new client secret in App registration → Certificates & secrets |

---

## Part 5: Azure DevOps Pipeline (Deploy from Azure Repos)

Deploy the discovery service from Azure DevOps Pipelines.

### 5.1 Create pipeline

1. **Pipelines** → **New pipeline** → **Azure Repos Git**
2. Select your repo
3. **Starter pipeline** (or **Azure Web App for Python** template if available)

### 5.2 Pipeline YAML

Create or edit `azure-pipelines.yml` in repo root:

```yaml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

variables:
  pythonVersion: '3.11'
  azureSubscription: '<your-service-connection-name>'
  webAppName: 'aiuso'
  resourceGroup: 'AI-USO'

steps:
- task: UsePythonVersion@0
  inputs:
    versionSpec: '$(pythonVersion)'

- script: |
    pip install -r requirements.txt
  displayName: 'Install dependencies'

- task: ArchiveFiles@2
  inputs:
    rootFolderOrFile: '$(Build.SourcesRoot)'
    includeRootFolder: false
    archiveType: 'zip'
    archiveFile: '$(Build.ArtifactStagingDirectory)/app.zip'
    replaceExistingArchive: true

- task: AzureWebApp@1
  inputs:
    azureSubscription: '$(azureSubscription)'
    appName: '$(webAppName)'
    package: '$(Build.ArtifactStagingDirectory)/app.zip'
```

Replace `azureSubscription` with your service connection name, `webAppName` and `resourceGroup` with your values.

### 5.3 Configure App Service startup command

The discovery service runs from `services/discovery-service/`. Set the startup command so App Service runs it correctly.

**Option A: Azure Portal**

1. App Service → **Configuration** → **General settings**
2. **Startup Command** (choose one):

   **Uvicorn** (already in requirements.txt):
   ```bash
   cd /home/site/wwwroot/services/discovery-service && uvicorn main:app --host 0.0.0.0 --port 8000
   ```

   **Gunicorn** (add `gunicorn` to requirements.txt for production):
   ```bash
   cd /home/site/wwwroot/services/discovery-service && gunicorn --bind 0.0.0.0:8000 --worker-class uvicorn.workers.UvicornWorker main:app
   ```

**Option B: Azure CLI**

```bash
# Uvicorn (no extra deps)
az webapp config set --name $APP_NAME --resource-group $RESOURCE_GROUP \
  --startup-file "cd /home/site/wwwroot/services/discovery-service && uvicorn main:app --host 0.0.0.0 --port 8000"
```

**Option C: Use a custom startup script**

Create `startup.sh` in repo root and set it as startup command. Ensure the pipeline deploys it.

**Note:** App Service extracts the zip to `/home/site/wwwroot/`. The discovery service imports `packages/shared`, so the full repo structure must be deployed.

### 5.4 App settings (environment variables)

Set `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, etc. in App Service:

```bash
az webapp config appsettings set --name $APP_NAME --resource-group $RESOURCE_GROUP \
  --settings SUPABASE_URL="https://xxx.supabase.co" SUPABASE_SECRET_KEY="sb_secret_..." ENVIRONMENT="staging"
```

Or in Portal: **Configuration** → **Application settings** → **New application setting**.

---

## Part 6: GitHub + Azure (alternative)

If your repo is on **GitHub** instead of Azure DevOps:

### 6.1 Publish profile for GitHub Actions

```bash
az webapp deployment list-publishing-profiles --name $APP_NAME --resource-group $RESOURCE_GROUP --xml
```

Copy the full XML. Add as GitHub secret `AZURE_WEBAPP_PUBLISH_PROFILE`. Use `azure/webapps-deploy@v2` in the workflow.

### 6.2 GitHub does not support Azure DevOps Deployment Center

The App Service Deployment Center source connection does not accept Azure DevOps repo URLs. Use Pipelines (Azure DevOps) or GitHub Actions (GitHub) instead.

---

## Quick reference

| Task | Command / Location |
|------|--------------------|
| Azure login | `az login` |
| List subscriptions | `az account list -o table` |
| Set subscription | `az account set -s <name>` |
| Add Azure DevOps remote | `git remote add azure <url>` |
| Add App Service remote | `git remote add azure-app <git-url>` |
| Deploy via Local Git | `git push azure-app main` |
| Deploy via Pipeline | Push to main → Pipeline runs |
| Create resource group | `az group create -n <name> -l eastus` |
| Create web app | `az webapp create ...` |
| Service connection | Project Settings → Service connections |
| Startup command | App Service → Configuration → General settings |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `az: command not found` | Install Azure CLI; ensure it's in PATH |
| `Authentication failed` for Git | Use PAT (Azure DevOps) or deployment credentials (App Service) |
| `Permission denied` on push | Check PAT scope includes Code (Read & write) |
| `Repository not found` | Verify org/project/repo name and your access |
| Resource group not loading (service connection) | Use **Credential: Secret** instead of Workload identity federation |
| Failed to obtain JWT (manual service connection) | Verify Client ID, Tenant ID, Secret; run `az role assignment create` |
| App Service 502 after deploy | Set startup command (Part 5.3); ensure `gunicorn` in requirements.txt if using it; check logs: `az webapp log tail -n $APP_NAME -g $RESOURCE_GROUP` |
| Invalid RepoUrl format (Deployment Center) | App Service Deployment Center does not support Azure DevOps URLs; use Pipelines instead |
