# USO Portal

Next.js application for the AI Universal Service Orchestrator, comprising:

- **Partner Portal** (`/`): Landing page, self-registration, dashboard, products, schedule, orders, and more
- **Platform Portal** (`/platform`): Platform admin for partner onboarding, super admins, and config

## Tech Stack

- Next.js 15 (App Router)
- Tailwind CSS v4
- Clerk (auth)
- Supabase (database)
- FullCalendar (product availability)

## Setup

1. Copy `.env.example` to `.env.local` and fill in:
   - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`
   - `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`

2. Install and run:

```bash
npm install
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000)

## Bootstrap first platform admin

The platform portal (`/platform`) is restricted to users in `platform_admins`. To add your first admin:

1. Sign in to the app and go to [Clerk Dashboard](https://dashboard.clerk.com) → Users → copy your **User ID** (e.g. `user_2abc123`)
2. In Supabase SQL editor, run:
   ```sql
   INSERT INTO platform_admins (clerk_user_id, scope) VALUES ('user_2abc123', 'all');
   ```
3. Sign in again at `/platform/login` to access the platform admin.

## Deployment (Vercel)

1. Push to GitHub and connect the repo to Vercel
2. Set environment variables in Vercel Dashboard
3. Deploy from `apps/portal` or set root directory to `apps/portal`

## Design Tokens

The app uses CSS custom properties for theming. See `app/globals.css` for:
- Colors (`--color-primary`, etc.)
- Font (`--font-family`, `--font-family-heading`)
- Font size (`--text-xs`, `--text-sm`, …)
- Spacing (`--spacing-xs`, …)
- Sizing (`--radius-sm`, `--content-max-width`, `--sidebar-width`)

Theme switcher in the header supports: light, dark, ocean, forest, slate.
