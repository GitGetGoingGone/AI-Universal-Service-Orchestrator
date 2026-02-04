# Authentication Setup (Clerk Integration)

Clerk provides authentication for customers, partners, admins, and AI agent handoff.

## Clerk Project Setup

### 1. Create Application

1. Go to [clerk.com](https://clerk.com) → Create Application
2. Choose sign-in options: Email, Google, etc.
3. Name your application (e.g., `USO Dev`)

### 2. Get API Keys

**Dashboard → API Keys**:

- **Publishable key** (`pk_test_...`): Use in frontend, safe to expose
- **Secret key** (`sk_test_...`): Use in backend only, never expose

Add to `.env`:

```env
CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
```

### 3. Configure Allowed Origins

**Dashboard → Settings → Paths** (or Domains):

- Add `http://localhost:3000` for local dev
- Add `http://localhost:8000` if Clerk runs on API
- Add your staging/production domains when ready

## Local Development Authentication

### Development Instance

Clerk provides a development instance by default:

- Uses `pk_test_` and `sk_test_` keys
- Supports unlimited test users
- No production data

### Redirect URLs

**Dashboard → Configure → Paths**:

- **Sign-in URL**: `/sign-in`
- **Sign-up URL**: `/sign-up`
- **After sign-in URL**: `/` or your app home
- **After sign-up URL**: `/`

For localhost, Clerk allows `http://localhost:*` by default in dev.

## Test Users

### Create via Dashboard

1. **Dashboard → Users → Create User**
2. Enter email, password (or use "Create user" with email only)
3. Optionally add metadata (roles, etc.)

### Create via API

```bash
curl -X POST https://api.clerk.com/v1/users \
  -H "Authorization: Bearer sk_test_..." \
  -H "Content-Type: application/json" \
  -d '{
    "email_address": ["dev@example.com"],
    "password": "YourSecurePassword123!",
    "first_name": "Dev",
    "last_name": "User"
  }'
```

### Sync to `users` Table

When a user signs up in Clerk, sync to your `users` table via webhook or on first API call:

```python
# Example: Ensure user exists in DB
async def get_or_create_user(clerk_user_id: str) -> User:
    user = await db.get_user(clerk_user_id)
    if not user:
        clerk_user = await clerk_client.users.get(clerk_user_id)
        user = await db.create_user(
            id=clerk_user_id,
            email=clerk_user.email_addresses[0].email_address,
            legal_name=clerk_user.legal_name or clerk_user.first_name,
            display_name=clerk_user.first_name,
        )
    return user
```

## Role/Permission Setup (RBAC)

### Clerk Metadata

Store roles in Clerk user metadata:

**Dashboard → Configure → User & Authentication → Metadata**:

Add custom claims:

- `role`: `customer` | `partner` | `hub` | `admin` | `gig_worker`
- `partner_id`: UUID (if role is partner)
- `capabilities`: Array of capability tags (optional)

### Role Definitions

| Role | Description | Access |
|------|-------------|--------|
| `customer` | End user | Browse, order, support chat |
| `partner` | Vendor/retailer | Partner portal, products, orders |
| `hub` | Hub operator | Hub dashboard, negotiations |
| `gig_worker` | Delivery/worker | Task queue, status updates |
| `admin` | Platform admin | Admin dashboard, config |

### Setting Roles

**Via Dashboard**: Users → Select user → Metadata → Add `role`

**Via API**:

```python
await clerk_client.users.update_metadata(user_id, {"role": "partner", "partner_id": "uuid"})
```

### Backend Validation

```python
from clerk_backend_api import Clerk

def require_role(required: str):
    async def dependency(request: Request):
        user_id = request.state.user_id  # From Clerk middleware
        user = await clerk_client.users.get(user_id)
        role = user.public_metadata.get("role", "customer")
        if role != required and role != "admin":
            raise ForbiddenError("Insufficient permissions")
        return user_id
    return dependency
```

## Link Account Flows (Zero-Friction Auth)

For Chat-First / Headless: AI agents (ChatGPT, Gemini) need to link user identity without login screens.

### Flow

1. User initiates from chat (e.g., "Order flowers")
2. AI agent redirects to Link Account URL with `platform` and `thread_id`
3. User signs in once (Clerk)
4. System creates `account_links` record: `user_id` ↔ `platform` + `thread_id`
5. Future requests from that thread are attributed to the user

### Implementation

- **Agentic Handoff**: Clerk supports SSO 2.0 for AI agents
- **Account links table**: `account_links` (see database schema)
- **Token storage**: Delegated OAuth tokens in `account_links` (hashed)

Reference: Plan `01-overview.md` – Zero-Friction Auth, Link Account Flows

## Clerk Webhook (User Sync)

**When you need it**: Not for initial setup. Add when you have a sign-up flow (Next.js app, partner portal) and want users automatically synced to your `users` table. Until then, use "lazy sync" (create user in DB on first API call).

**When to add**:
- Building the Next.js web app with Clerk sign-in/sign-up
- Building the Partner Portal (Module 9) with partner registration
- Need real-time user list in admin (users in DB before first API call)
- Need to sync user updates/deletes from Clerk

**Until then**: Skip `CLERK_WEBHOOK_SECRET`. Use lazy sync in your API (see "Sync to users Table" above).

### Setup

1. **Dashboard → Webhooks → Add Endpoint**
2. URL: `https://your-api.com/webhooks/clerk`
3. Events: `user.created`, `user.updated`, `user.deleted`
4. Copy signing secret → `CLERK_WEBHOOK_SECRET`

### Handler

```python
@app.post("/webhooks/clerk")
async def clerk_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.body()
    sig = request.headers.get("svix-signature")
    # Verify with CLERK_WEBHOOK_SECRET (Svix)
    # Parse payload, upsert/delete from users table
    background_tasks.add_task(sync_user, payload)
    return {"received": True}
```

## Next Steps

- [Development Environment](./DEVELOPMENT_ENVIRONMENT.md)
- [Database Setup](./DATABASE_SETUP.md) – `users` table, `account_links`
- Plan `02-architecture.md` – Chat-First auth, Agentic Consent Manager
