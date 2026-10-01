# EVE Healthcare Submission Checklist

| Assignment item | Implementation |
|---|---|
| Signup, login, JWT, validation | `app/routers/auth.py`, `app/security.py`, `app/schemas.py` |
| Diagnostic centres + tests | `app/routers/centres.py`, `app/routers/tests.py` |
| Booking with patient/test/centre/time/amount/status | `app/routers/bookings.py`, `app/models.py` |
| Mock payment + booking update | `app/routers/payments.py`, `app/services/payment_service.py` |
| Idempotent payment webhook | `WebhookEvent.event_id` unique + transactional handler |
| Invalid requests / IDs / authorization | FastAPI validation + explicit `401/403/404/409` handling |
| PostgreSQL | `docker-compose.yml`, `DATABASE_URL` |
| Swagger/OpenAPI | FastAPI `/docs`, `/openapi.json` |
| Tests | `tests/` |
| Structured logging | request middleware in `app/main.py` |
| Pagination | `GET /centres?page=&page_size=` |
| Retry/idempotency handling | Payment `Idempotency-Key` + webhook event deduplication |
| Docker | `Dockerfile`, `docker-compose.yml` |
| README | `README.md` |
| CI | `.github/workflows/ci.yml` |

## Before submission

- Change `JWT_SECRET_KEY` and `WEBHOOK_SECRET` in the submitted deployment environment.
- Do not commit `.env`.
- Push the repository to GitHub.
- Paste the GitHub repository URL into the campus placement assignment form.
