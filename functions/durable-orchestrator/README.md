# Durable Orchestrator - The Brain (Month 0)

Base orchestrator template for the AI Universal Service Orchestrator. Implements the Azure Durable Functions pattern: checkpoint state, sleep for extended periods, wake on external events.

## Features

- **Checkpoint state**: Orchestrator state persisted at each `yield`
- **Sleep/wake**: Can sleep for days/weeks with near $0 cost (Consumption plan)
- **External events**: Wake up via HTTP when external event is raised
- **Wait-for-event pattern**: Foundation for Standing Intents (Module 23), Omnichannel (Module 24)

## Prerequisites

- Python 3.9+ (3.11 recommended)
- [Azure Functions Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local) v4
- **Storage**: Azure Storage account (or [Azurite](https://learn.microsoft.com/en-us/azure/storage/common/storage-use-azurite) for local dev)

### Local storage (Azurite)

```bash
# Install Azurite (or use Docker)
npm install -g azurite

# Run Azurite (default: blob + queue on 10000, table on 10002)
azurite --silent --location ./azurite-data
```

Update `local.settings.json`:

```json
{
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true"
  }
}
```

`UseDevelopmentStorage=true` uses Azurite at default ports.

### Azure Storage (remote)

Use a real connection string in `local.settings.json`:

```json
{
  "Values": {
    "AzureWebJobsStorage": "DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net"
  }
}
```

## Run locally

**Important**: Durable Functions requires storage. You must either:
- **Option A**: Start Azurite in a separate terminal first, or
- **Option B**: Use a real Azure Storage connection string in `local.settings.json`

```bash
# Terminal 1: Start Azurite (required if using UseDevelopmentStorage=true)
azurite --silent --location ./azurite-data

# Terminal 2: Run the function app
cd functions/durable-orchestrator
cp local.settings.example.json local.settings.json  # if first time
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate  — MUST activate before func start
pip install -r requirements.txt
func start   # Run from same terminal where venv is activated
```

Requires [Azure Functions Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local) v4. Use Python 3.11+ (3.9 is EOL).

Default URL: `http://localhost:7071`

## API

### Start orchestration

```bash
curl -X POST http://localhost:7071/api/orchestrators/base_orchestrator \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "wait_event_name": "WakeUp"}'
```

Response (202) includes `id` (instance_id) and `statusQueryGetUri`.

### Check status

```bash
# Replace INSTANCE_ID with the "id" from the start response
curl http://localhost:7071/api/orchestrators/INSTANCE_ID/status
```

**Alternative**: Use `statusQueryGetUri` from the start response (built-in endpoint, always works):

```bash
curl "http://localhost:7071/runtime/webhooks/durabletask/instances/INSTANCE_ID?taskHub=TestHubName&connection=AzureWebJobsStorage&code=YOUR_CODE"
```

### Raise external event (wake orchestrator)

```bash
# Replace INSTANCE_ID with the "id" from the start response (e.g. 70d9459ade6e46ad9c8e05721901f9ab)
curl -X POST http://localhost:7071/api/orchestrators/INSTANCE_ID/raise/WakeUp \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

**Alternative**: Use `sendEventPostUri` from the start response—replace `{eventName}` with `WakeUp`:

```bash
curl -X POST "http://localhost:7071/runtime/webhooks/durabletask/instances/INSTANCE_ID/raiseEvent/WakeUp?taskHub=TestHubName&connection=AzureWebJobsStorage&code=YOUR_CODE" \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

## End-to-end test

1. **Start** orchestration → copy the `id` from the response (e.g. `70d9459ade6e46ad9c8e05721901f9ab`)
2. **Check status** → `curl .../INSTANCE_ID/status` → `runtimeStatus: "Running"` (waiting for event)
3. **Raise event** → `curl -X POST .../INSTANCE_ID/raise/WakeUp -d '{"approved": true}'`
4. **Check status** → `runtimeStatus: "Completed"`

## Project structure

```
functions/durable-orchestrator/
├── function_app.py      # Orchestrator, activities, HTTP triggers
├── host.json            # Durable Task config
├── local.settings.json  # Local config (not in git)
├── requirements.txt
├── .funcignore
└── README.md
```

## Deploy to Azure

```bash
# Create Function App (Linux, Python 3.11)
az functionapp create \
  --resource-group <rg> \
  --consumption-plan-location eastus \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --name <app-name> \
  --storage-account <storage-name>

# Deploy
func azure functionapp publish <app-name>
```

## Cost

- **Consumption plan**: Pay only for execution time
- **Waiting**: $0 while orchestrator sleeps (no charge for `wait_for_external_event`)
- Typical: 7-day wait ≈ 168 seconds execution ≈ ~$0.0001

## Troubleshooting

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: No module named 'azure.durable_functions'` | Activate the venv before `func start`: `source .venv/bin/activate` (Windows: `.venv\Scripts\activate`). Then `pip install -r requirements.txt` and `func start`. The Functions worker uses the active Python. |
| `Connection refused (127.0.0.1:10000)` | Azurite is not running. Start it: `azurite --silent --location ./azurite-data` in a separate terminal. Or use a real Azure Storage connection string in `local.settings.json`. |
| `Python 3.9 reached EOL` | Use Python 3.11+: `pyenv install 3.11` then `pyenv local 3.11` (or create venv with `python3.11 -m venv .venv`). |
| `The binding type(s) 'orchestrationTrigger' are not registered` | Add `extensionBundle` to `host.json` (see host.json in this folder). |
