# Git and Azure CLI Setup

Instructions for connecting Git with Azure using the command line.

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
az devops configure --defaults organization=https://dev.azure.com/aiuso 
az devops configure --defaults project=aiuso


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
RESOURCE_GROUP="uso-staging-rg"
APP_NAME="uso-discovery-staging"
LOCATION="eastus"

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

```bash
# Get Git clone URL
az webapp deployment source show --name $APP_NAME --resource-group $RESOURCE_GROUP

# Create deployment credentials (one-time)
az webapp deployment user set --user-name <username> --password <password>
# Or use: az webapp deployment list-publishing-credentials
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

## Part 4: GitHub + Azure (via Azure CLI)

If your repo is on **GitHub** and you want to deploy to Azure:

### 4.1 Connect GitHub to Azure App Service

```bash
# One-time: GitHub token with repo scope
# Create at: GitHub → Settings → Developer settings → Personal access tokens

az webapp deployment source config --name $APP_NAME --resource-group $RESOURCE_GROUP \
  --repo-url https://github.com/<org>/<repo> \
  --branch main \
  --manual-integration
# Prompts for GitHub token
```

### 4.2 Or use GitHub Actions (no Azure Git remote)

Deploy via GitHub Actions instead of `git push` to Azure. Azure CLI is used to create the app; deployment is handled by the workflow.

```bash
# Create app (as in 3.1)
# Get publish profile for GitHub Actions
az webapp deployment list-publishing-profiles --name $APP_NAME --resource-group $RESOURCE_GROUP --xml
# Add output as GitHub secret AZURE_WEBAPP_PUBLISH_PROFILE
```

---

## Part 5: Azure DevOps Pipelines (YAML)

Use Azure DevOps for CI/CD instead of GitHub Actions:

```bash
# Create pipeline from repo
az pipelines create --name "discovery-service" \
  --repository <repo-id> \
  --repository-type tfsgit \
  --yml-path azure-pipelines.yml
```

Create `azure-pipelines.yml` in repo root for build and deploy.

---

## Quick reference

| Task | Command |
|------|---------|
| Azure login | `az login` |
| List subscriptions | `az account list -o table` |
| Set subscription | `az account set -s <name>` |
| Add Azure DevOps remote | `git remote add azure <url>` |
| Add App Service remote | `git remote add azure-app <git-url>` |
| Deploy to App Service | `git push azure-app main` |
| Create resource group | `az group create -n <name> -l eastus` |
| Create web app | `az webapp create ...` |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `az: command not found` | Install Azure CLI; ensure it's in PATH |
| `Authentication failed` for Git | Use PAT (Azure DevOps) or deployment credentials (App Service) |
| `Permission denied` on push | Check PAT scope includes Code (Read & write) |
| `Repository not found` | Verify org/project/repo name and your access |
| App Service 502 after deploy | Check startup command, Python version, and app logs: `az webapp log tail -n $APP_NAME -g $RESOURCE_GROUP` |
