# Team Pulse

**Zero-input async standups.** Team Pulse generates daily standup summaries
from the signal your team already produces — no forms, no Slack-bot nags, no
"what did you do yesterday?" rituals. Members get an automatic digest; managers
get a pulse on the team without chasing anyone.
And this is test number 2

> Status: early scaffold. The pieces below are wired up but most product logic
> is still TODOooo.

## Monorepo layout

```
team-pulse/
├── backend/    FastAPI server (Python) + Supabase
└── frontend/   Next.js 14 (App Router) + Tailwind + shadcn/ui
```

## Backend (`/backend`)

FastAPI service. Structure:

```
backend/
├── requirements.txt
├── .env.example
└── app/
    ├── main.py              # FastAPI app + router registration
    ├── config.py            # Pydantic settings (reads .env)
    ├── routes/              # HTTP endpoints (e.g. health)
    ├── integrations/        # External clients (Supabase, etc.)
    ├── services/            # Business logic
    └── models/              # Pydantic data models
```

### Run it

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in your Supabase credentials
uvicorn app.main:app --reload --port 8000
```

- Health check: http://localhost:8000/health
- Interactive docs: http://localhost:8000/docs

## Frontend (`/frontend`)

Next.js 14 App Router with Tailwind and shadcn/ui preconfigured.

```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx             # landing
│   ├── dashboard/page.tsx   # the dashboard
│   └── globals.css          # Tailwind + shadcn CSS variables
├── components/ui/           # shadcn components (button, card, ...)
├── lib/utils.ts             # cn() helper
└── components.json          # shadcn config
```

### Run it

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

- App: http://localhost:3000
- Dashboard: http://localhost:3000/dashboard

Add more shadcn components with, e.g., `npx shadcn@latest add dialog`.

## Configuration

| Variable               | Where             | Purpose                          |
| ---------------------- | ----------------- | -------------------------------- |
| `SUPABASE_URL`         | `backend/.env`    | Supabase project URL             |
| `SUPABASE_KEY`         | `backend/.env`    | Supabase API key                 |
| `NEXT_PUBLIC_API_URL`  | `frontend/.env.local` | Base URL of the backend API  |
