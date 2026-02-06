# Azure Functions Python 4 - Durable Orchestrator
# Deploy to Render as Docker Web Service
FROM mcr.microsoft.com/azure-functions/python:4-python3.11

ENV AzureWebJobsScriptRoot=/home/site/wwwroot
ENV AzureFunctionsJobHost__Logging__Console__IsEnabled=true

# Render uses port 10000 for Docker; Azure Functions reads WEBSITES_PORT
ENV WEBSITES_PORT=10000

# Install Azure Functions Core Tools (base image lacks 'func' CLI)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg ca-certificates \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/microsoft-debian-bullseye-prod bullseye main" > /etc/apt/sources.list.d/dotnetdev.list \
    && apt-get update && apt-get install -y --no-install-recommends azure-functions-core-tools-4 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt /home/site/wwwroot/
RUN cd /home/site/wwwroot && pip install --no-cache-dir -r requirements.txt

# Copy function app
COPY . /home/site/wwwroot

# Start the Functions host (func reads WEBSITES_PORT for port binding)
CMD ["func", "host", "start"]
