# Azure Functions Python 4 - Durable Orchestrator
# Deploy to Render as Docker Web Service
FROM mcr.microsoft.com/azure-functions/python:4-python3.11

ENV AzureWebJobsScriptRoot=/home/site/wwwroot
ENV AzureFunctionsJobHost__Logging__Console__IsEnabled=true

# Render uses port 10000 for Docker; Azure Functions reads WEBSITES_PORT
ENV WEBSITES_PORT=10000

# Install Azure Functions Core Tools via npm (base image lacks 'func' CLI)
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm \
    && npm install -g azure-functions-core-tools@4 --unsafe-perm true \
    && apt-get remove -y npm && apt-get autoremove -y \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /root/.npm

# Copy and install dependencies
COPY requirements.txt /home/site/wwwroot/
RUN cd /home/site/wwwroot && pip install --no-cache-dir -r requirements.txt

# Copy function app
COPY . /home/site/wwwroot

# Create local.settings.json if missing (func expects host.json or local.settings.json)
# Real config comes from env vars (AzureWebJobsStorage, etc.) at runtime
RUN [ -f /home/site/wwwroot/local.settings.json ] || echo '{"IsEncrypted":false,"Values":{}}' > /home/site/wwwroot/local.settings.json

# func host start looks for host.json in current directory
WORKDIR /home/site/wwwroot

# Start the Functions host (bind to 0.0.0.0 so Render can reach it)
# Use $PORT from Render, fallback to 10000
CMD ["sh", "-c", "func host start --host 0.0.0.0 --port ${PORT:-10000}"]
