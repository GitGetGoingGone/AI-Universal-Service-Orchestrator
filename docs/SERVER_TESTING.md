# Server-Based Testing

This project uses **server-based testing**: tests run against a **deployed service** over HTTP, not against in-process mocks or TestClient. This validates real deployments (staging, production) and catches integration issues that unit tests miss.

## Philosophy

| Local/Unit Testing | Server-Based Testing |
|--------------------|----------------------|
| TestClient, mocks, in-process | Real HTTP to deployed URL |
| Fast, isolated, no network | Slower, requires running server |
| Catches logic bugs | Catches deployment, config, DB, network issues |
| Run on every save | Run in CI after deploy, or on-demand |

**We prioritize server tests** for critical paths: health, readiness, and core API contracts.

## Prerequisites

1. **Deployed service** – Discovery service must be running at a reachable URL.
2. **Environment variable** – `DISCOVERY_SERVICE_URL` (or `API_BASE_URL`) points to the server.

**No staging yet?** See [Staging Setup](STAGING_SETUP.md) for step-by-step instructions.

## Running Server Tests

### Against Staging (CI / Manual)

```bash
# Set the server URL
export DISCOVERY_SERVICE_URL=https://discovery-staging.example.com

# Run server tests
pytest tests/ -v -m server
```

### Against Local Server (Quick Check)

If you run the service locally (`uvicorn main:app --reload` in `services/discovery-service/`):

```bash
export DISCOVERY_SERVICE_URL=http://localhost:8000
pytest tests/ -v -m server
```

### Against Production (Smoke Only)

Use with caution. Prefer staging for full suites.

```bash
export DISCOVERY_SERVICE_URL=https://api.example.com
pytest tests/ -v -m "server and not destructive"
```

## Test Structure

```
tests/
├── conftest.py           # BASE_URL fixture from env
├── test_discovery_health.py   # Health, ready, root
└── test_discovery_api.py     # /api/v1/discover contract
```

- **`conftest.py`**: Reads `DISCOVERY_SERVICE_URL` or `API_BASE_URL`, provides `base_url` fixture.
- **Health tests**: Assert `/health`, `/ready`, `/` return expected status and shape.
- **API tests**: Assert `/api/v1/discover` returns valid JSON-LD, Adaptive Card, and data shape per OpenAPI.

## CI Integration

Server tests run in GitHub Actions **after** a successful deploy to staging:

1. Deploy workflow pushes to staging.
2. Test workflow runs with `DISCOVERY_SERVICE_URL` set to staging URL.
3. Tests must pass before promoting to production (if you use approval gates).

See `.github/workflows/server-tests.yml`.

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DISCOVERY_SERVICE_URL` | Base URL for discovery service | `https://discovery-staging.example.com` |
| `API_BASE_URL` | Fallback if `DISCOVERY_SERVICE_URL` not set | Same as above |

## Adding New Server Tests

1. Create `tests/test_<service>_<area>.py`.
2. Use `@pytest.mark.server` so they can be filtered.
3. Use the `base_url` fixture (or `discovery_base_url` for discovery service).
4. Use `httpx` for HTTP requests; assert status codes and response structure.
5. Avoid tests that mutate production data; use staging-only fixtures if needed.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `DISCOVERY_SERVICE_URL not set` | Export the variable or set in CI secrets |
| Connection refused / timeout | Ensure service is deployed and reachable from runner |
| 502/503 on `/ready` | Check DB and other dependencies for the deployed service |
| Tests pass locally, fail in CI | CI may hit different URL; verify staging URL and secrets |
