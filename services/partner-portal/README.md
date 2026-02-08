# Partner Portal (Module 9)

Generic Capability Portal for partner onboarding, product registration, and webhook configuration.

## Features

- **Partner onboarding**: Create partner records (business name, contact email)
- **Product registration**: Add products linked to partners (appear in Discovery)
- **Webhook config**: Set URL for change requests (Omnichannel Broker will POST to it)

## Run locally

```bash
# From project root
uvicorn services.partner_portal.main:app --reload --port 8003
```

Or from this directory:
```bash
cd services/partner-portal
uvicorn main:app --reload --port 8003
```
(Requires project root in PYTHONPATH for shared packages)

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/onboard | Onboarding form (HTML) |
| POST | /api/v1/onboard | Create partner |
| GET | /api/v1/partners | List partners |
| GET | /api/v1/partners/{id} | Get partner |
| GET | /api/v1/partners/{id}/products | Product management (HTML) |
| POST | /api/v1/partners/{id}/products | Add product |
| GET | /api/v1/partners/{id}/settings | Webhook settings (HTML) |
| POST | /api/v1/partners/{id}/webhook | Save webhook URL |

## Environment

- `SUPABASE_URL`, `SUPABASE_SECRET_KEY` (or `SUPABASE_SERVICE_KEY`)
