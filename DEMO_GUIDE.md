# EVE Healthcare — Recruiter Demo Script

Use this sequence when showing the assignment in a placement/interview review.

## 60-second demo

**1. Home**

Open `/` and point out the healthcare booking workflow and live service health indicator.

**2. Login**

Click **Try demo access**. The seeded patient account is used.

**3. Find a Test**

Use the catalogue search. Open a test card and book an appointment for a future date/time.

**4. Payment**

Open **My Bookings** and choose **Simulate success**. The booking should move from `PENDING` to `CONFIRMED`.

**5. Admin**

Sign out, choose **Sign in**, then use the admin demo credentials. Open **Admin** to create a centre/test or attach a test with a centre-specific price.

**6. Webhook idempotency**

In Admin, enter a payment ID and event ID in the webhook simulator. Send the event twice with the same event ID. The second response should say that the duplicate event was ignored safely.

**7. API review**

Open `/docs` and show the required endpoints, especially:

- `/auth/signup`
- `/auth/login`
- `/centres`
- `/tests`
- `/bookings`
- `/payments/`
- `/payments/webhook/`

## Talking points

- Passwords are stored as scrypt-derived hashes.
- JWTs protect patient/admin operations.
- Centre/test has a unique mapping and centre-specific price.
- Booking stores an amount snapshot so later catalogue price changes do not alter past bookings.
- Payment is one-per-booking and can be retried safely with an idempotency key.
- Webhook `event_id` is unique, so the same provider event is processed once.
- Terminal payment states are monotonic to prevent delayed events from reversing a completed outcome.
- Tests cover auth, admin authorization, booking/payment, webhook idempotency and ownership failures.
