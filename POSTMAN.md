# Quick Postman Flow

1. Start the API with Docker Compose.
2. Run `docker compose exec api python scripts/seed.py`.
3. Login with the seeded admin account to create centres/tests if needed.
4. Signup a patient and login.
5. Attach a test to a centre.
6. Create a future booking as the patient.
7. Call `POST /payments/` with `simulate_status: SUCCESS` and an `Idempotency-Key`.
8. Replay the same request to demonstrate idempotency.
9. Call `POST /payments/webhook/` with the shared secret and a unique `event_id`.
10. Replay the same webhook event and verify `processed` becomes `false`.

Swagger at `/docs` can be used instead of Postman for the full flow.
