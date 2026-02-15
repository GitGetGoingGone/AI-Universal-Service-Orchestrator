# USO Unified Chat

End-user chat app. Calls the orchestrator backend; LLM provider/model is configured in the admin portal.

## Features

- Chat UI: message list, input, adaptive cards
- Proxies to `POST /api/v1/chat` on orchestrator

## Environment

### Vercel (Project → Settings → Environment Variables)

| Variable | Required | Description |
|----------|----------|-------------|
| `ORCHESTRATOR_URL` | Yes | Orchestrator service URL (e.g. https://uso-orchestrator.onrender.com) |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL (for thread persistence) |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Supabase service role key (server-side, bypasses RLS) |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | For payments | Stripe publishable key (pk_test_... or pk_live_...) — enables PaymentModal |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | For auth | Clerk publishable key — enables sign-in and cross-device threads |
| `CLERK_SECRET_KEY` | For auth | Clerk secret key (server-side) |

**Note:** `NEXT_PUBLIC_*` vars are exposed to the browser. Never put secrets there.

## Run

```bash
npm install
npm run dev
# http://localhost:3011
```

## Deploy

Deploy to Vercel. Add the environment variables above in **Project → Settings → Environment Variables**. Redeploy after changing env vars.
