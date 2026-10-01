# EVE Healthcare - SDE Intern Assignment

A production-minded FastAPI backend with a responsive healthcare web demo at `/`, so the assignment can be published as a single recruiter-accessible website. It is a website demo, not a mobile app.

The backend covers diagnostic test discovery, bookings, simulated payments, and idempotent payment webhooks.

This implementation follows the assignment requirements: JWT authentication, diagnostic centres/tests, authenticated bookings, mock payment processing, idempotent webhook handling, validation/authorization, PostgreSQL support, Docker, OpenAPI docs, pagination, structured logs, and automated tests.

## Tech stack

- Python 3.13
- FastAPI + Pydantic v2
- SQLAlchemy 2.0
- PostgreSQL 16 (preferred runtime database)
- PyJWT
- Docker + Docker Compose
- Pytest + HTTPX

## Architecture

```text
app/
├── main.py                  # FastAPI app, middleware, health check
├── config.py                # Environment-driven settings
├── db.py                    # SQLAlchemy engine/session
├── models.py                # Database entities and relationships
├── schemas.py               # Request/response validation
├── security.py              # Password hashing + JWT auth + roles
├── utils.py                 # Logging configuration
├── services/
│   └── payment_service.py   # Payment state machine + webhook idempotency
└── routers/
    ├── auth.py
    ├── centres.py
    ├── tests.py
    ├── bookings.py
    └── payments.py

scripts/
└── seed.py                  # Sample admin, centres, and tests

tests/
├── conftest.py
└── test_api.py
```

## Presentation layer

The backend includes a lightweight, healthcare-themed landing page and a customized dark Swagger UI for a polished evaluator experience.

- Home dashboard: `http://localhost:8000/`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

The visual layer is intentionally lightweight and does not add a frontend framework or change the backend assignment scope.

## Run locally with Docker

1. Copy the environment file:

```bash
cp .env.example .env
```

2. Start PostgreSQL + API:

```bash
docker compose up --build
```

3. Seed sample data (in a second terminal):

```bash
docker compose exec api python scripts/seed.py
```

4. Open the API documentation:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Health: `http://localhost:8000/health`

Sample seeded admin credentials:

```text
email: admin@evehealthcare.local
password: Admin@12345
```

Change the password before any real deployment.

## Run without Docker

The application can also use SQLite for a lightweight local development run because `DATABASE_URL` falls back to SQLite when not supplied. For the assignment submission, PostgreSQL is the intended database and the Docker setup uses it.

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

For PostgreSQL, set `DATABASE_URL`, `JWT_SECRET_KEY`, and `WEBHOOK_SECRET` in `.env` first.

## API overview

### Authentication

`POST /auth/signup`

```json
{
  "name": "Mithun",
  "email": "mithun@example.com",
  "password": "StrongPass@123"
}
```

`POST /auth/login`

```json
{
  "email": "mithun@example.com",
  "password": "StrongPass@123"
}
```

Use the returned bearer token as:

```text
Authorization: Bearer <token>
```

`GET /auth/me` returns the authenticated user.

### Diagnostic centres and tests

Public retrieval:

```text
GET /centres?page=1&page_size=20
GET /centres/{centre_id}
GET /centres/{centre_id}/tests
GET /tests
GET /tests/{test_id}
```

Admin management:

```text
POST  /centres
PATCH /centres/{centre_id}
DELETE /centres/{centre_id}
POST  /tests
PATCH /tests/{test_id}
DELETE /tests/{test_id}
POST /centres/{centre_id}/tests
DELETE /centres/{centre_id}/tests/{test_id}
```

The centre/test relationship stores the actual selling price at that centre. This allows the same test to have different prices at different locations.

### Booking

`POST /bookings`

```json
{
  "test_id": 1,
  "centre_id": 1,
  "appointment_at": "2030-01-15T10:30:00+05:30"
}
```

The API snapshots the offered centre price into `booking.amount`, preventing later catalogue price changes from changing an existing booking.

Other booking endpoints:

```text
GET  /bookings/me
GET  /bookings/{booking_id}
POST /bookings/{booking_id}/cancel
```

Only the booking owner (or an admin) can read/modify that booking.

### Simulated payment

`POST /payments/`

```json
{
  "booking_id": 1,
  "simulate_status": "SUCCESS"
}
```

`simulate_status` is optional. When omitted, the mock processor returns a simulated outcome. The optional field exists to make local testing deterministic.

Use an `Idempotency-Key` header to safely retry the payment request:

```text
Idempotency-Key: booking-1-attempt-1
```

Only one payment is allowed per booking.

### Payment webhook

`POST /payments/webhook/`

Header:

```text
X-Webhook-Secret: <WEBHOOK_SECRET>
```

Body:

```json
{
  "event_id": "evt_10001",
  "payment_id": 1,
  "event_type": "payment.updated",
  "status": "SUCCESS"
}
```

Every webhook `event_id` is stored under a unique database constraint. Replaying the same event returns `processed: false` and does not create a duplicate payment or booking.

The payment state machine is monotonic after a terminal state: a delayed webhook cannot change `SUCCESS` back to `FAILED` (or vice versa). This prevents out-of-order events from corrupting booking state.

## Database design

```text
users
  1 ─────── * bookings

bookings
  * ─────── 1 diagnostic_centres
  * ─────── 1 diagnostic_tests
  1 ─────── 0..1 payments

centre_tests
  diagnostic_centres * ─────── * diagnostic_tests
  (unique centre_id + test_id, with centre-specific price)

payments
  1 ─────── * webhook_events
  (unique booking_id, unique idempotency_key, unique provider_payment_id)
```

Key integrity controls:

- Unique user email
- Unique centre/test pairing
- Unique payment per booking
- Unique payment provider ID
- Unique idempotency key
- Unique webhook event ID
- Foreign keys for all ownership/catalogue references
- Booking amount stored as a decimal snapshot

## Booking state flow

```text
                  +----------------+
                  |     PENDING    |
                  +-------+--------+
                          |
                +---------+---------+
                |                   |
          payment SUCCESS     payment FAILED
                |                   |
                v                   v
        +---------------+    +---------------+
        |   CONFIRMED  |    |    FAILED     |
        +---------------+    +---------------+

PENDING -- cancel --> CANCELLED
```

A confirmed/failed/cancelled booking cannot be moved back to pending through the public API.

## Error handling and edge cases

The API explicitly handles:

- Duplicate registration (`409`)
- Invalid credentials (`401`)
- Missing/invalid JWT (`401`)
- Non-admin catalogue changes (`403`)
- Unknown centre/test/booking/payment IDs (`404`)
- Test not offered by a selected centre (`409`)
- Past appointment times (`422`)
- Unauthorized booking/payment access (`403`)
- Duplicate payment attempts (`409`, or the same result for a reused idempotency key)
- Duplicate webhook events (`200`, `processed: false`)
- Invalid webhook secret (`401`)
- Terminal payment-state regression (`ignored safely`)

## Tests

Run:

```bash
pytest -q
```

The test suite covers signup/login, role authorization, catalogue management, booking creation, payment idempotency, webhook idempotency, invalid IDs, and cross-user authorization.

Tests use an isolated in-memory SQLite database so the suite runs quickly without requiring a local PostgreSQL server.

## Assumptions

1. This is a small assignment service, so catalogue changes are admin-only and public endpoints expose active records.
2. Appointment capacity/slot inventory is outside the stated requirements, so each booking stores an appointment timestamp but no separate slot-capacity model is introduced.
3. Payments are simulated and there is no real money movement or payment gateway integration.
4. Webhooks are authenticated with a shared secret because even a simulated provider callback should not be unauthenticated.
5. `Base.metadata.create_all()` is used for the assignment-sized project. A production system would use Alembic migrations.

## What I would improve with more time

- Alembic migrations and migration CI checks
- PostgreSQL-backed integration tests in CI
- Redis for cache/rate limiting
- Celery/background processing for webhook retries and notifications
- Request correlation IDs and richer structured JSON logs
- Slot inventory/availability rules and appointment locking
- Email/SMS booking confirmations
- Refresh tokens and token revocation strategy
- CI pipeline for linting, tests, image build, and security scanning

## Interactive web demo

The root route (`/`) is now a complete responsive web experience connected to the real API. It is intentionally a website — not a mobile app — so an evaluator can open one public URL and inspect the working implementation.

The website includes:

- Patient signup/login with JWT-backed sessions
- Diagnostic catalogue and centre-specific pricing
- Appointment booking with future-date validation
- My Bookings workspace with cancellation
- Simulated payment success/failure flow
- Payment idempotency-key handling
- Admin console for centres, tests and centre/test pricing
- Payment webhook simulator for demonstrating duplicate-event protection (through an authenticated demo helper; the real provider endpoint is still `/payments/webhook/`)
- Direct links to Swagger UI and ReDoc

### Demo credentials

These are created by the idempotent seed script:

```text
Patient demo: demo@evehealthcare.local / Demo@12345
Admin demo:   admin@evehealthcare.local / Admin@12345
```

### Deploy as one public website

A `render.yaml` Blueprint is included for Render. It defines one Docker web service and one managed Postgres database, and wires `DATABASE_URL` to the web service through the database connection string. Render supports Docker services and database references through `fromDatabase`. See the official Blueprint reference for the current schema. 

After deployment, the recruiter can open the root URL directly, while `/docs` and `/redoc` remain available for technical review.

### Production note

The demo credentials are intentionally convenient for evaluation. For any real deployment, rotate the seeded passwords and webhook secret and use private/internal credentials.
