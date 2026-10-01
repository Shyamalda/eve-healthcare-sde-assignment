# EVE Healthcare — Website Deployment Guide

> **Developer:** Shyamalda · © 2026 Shyamalda — All rights reserved

The intended submission is a **single public website**. The root URL (`/`) is the recruiter-facing demo; `/docs` is the technical API view.

## Option A — Render Blueprint (recommended)

The repository contains `render.yaml`, which defines:

- one Docker web service
- one managed PostgreSQL database
- generated JWT and webhook secrets
- a `/health` deployment health check
- automatic database connection wiring through `DATABASE_URL`

### Steps

1. Push this repository to GitHub.
2. In Render, create a new Blueprint and select the GitHub repository.
3. Keep `render.yaml` at the repository root.
4. Let Render create the web service and Postgres database from the Blueprint.
5. Wait for the health check to become healthy.
6. Open the generated `https://...onrender.com/` URL.

### Public demo flow

1. Click **Try demo access**.
2. Open **Find a Test**.
3. Pick a diagnostic centre and test.
4. Create an appointment at a future time.
5. Open **My Bookings** and simulate payment success/failure.
6. For technical review, sign in using the admin demo and open **Admin**.
7. Use the webhook simulator with a payment ID. Re-send the same event ID to demonstrate idempotency.
8. Open `/docs` to inspect the actual `POST /payments/webhook/` provider endpoint.

## Option B — Railway

The current live demo is deployed on Railway as a public FastAPI web service backed by PostgreSQL. The connected GitHub repository is `Shyamalda/eve-healthcare-sde-assignment`.

Current public URLs:

- Website: https://eve-healthcare-sde-assignment-production.up.railway.app/
- Swagger: https://eve-healthcare-sde-assignment-production.up.railway.app/docs
- Health: https://eve-healthcare-sde-assignment-production.up.railway.app/health

For future updates, push changes to the `main` branch. The connected Railway service can rebuild and redeploy from the new commit.

## Demo credentials

```text
Patient
email: demo@evehealthcare.local
password: Demo@12345

Admin
email: admin@evehealthcare.local
password: Admin@12345
```

The container starts with the idempotent seed script, so the sample users, centres and tests are created automatically.

## Local website

```bash
cp .env.example .env
docker compose up --build
```

Then open:

```text
http://localhost:8000/
```

## Technical endpoints

```text
/
/docs
/redoc
/health
/openapi.json
```

The assignment's actual provider webhook remains:

```text
POST /payments/webhook/
```

The website uses the additional authenticated helper:

```text
POST /payments/webhook/demo/
```

This keeps the real webhook secret server-side while still giving a recruiter a one-click UI path to exercise the same idempotency logic.
