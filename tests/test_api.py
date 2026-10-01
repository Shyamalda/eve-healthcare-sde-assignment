from __future__ import annotations

from datetime import UTC, datetime, timedelta


def signup(client, email="patient@example.com"):
    return client.post(
        "/auth/signup",
        json={"name": "Test Patient", "email": email, "password": "StrongPass@123"},
    )


def login(client, email="patient@example.com"):
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "StrongPass@123"},
    )
    return response.json()["access_token"]


def admin_token(client):
    signup(client, "admin@example.com")
    from app.db import get_db
    from app.models import User
    from app.security import create_access_token
    # Promote the fixture user to admin directly through the app's dependency-managed DB.
    override = client.app.dependency_overrides[get_db]
    db = next(override())
    try:
        user = db.query(User).filter(User.email == "admin@example.com").one()
        user.role = "ADMIN"
        db.commit()
        return create_access_token(user)
    finally:
        db.close()


def test_health_and_signup_login(client):
    assert client.get("/health").json() == {"status": "ok"}
    created = signup(client)
    assert created.status_code == 201
    token = login(client)
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "patient@example.com"


def test_centre_and_test_management_requires_admin(client):
    patient_token = login(client) if signup(client).status_code == 201 else login(client)
    forbidden = client.post(
        "/centres",
        headers={"Authorization": f"Bearer {patient_token}"},
        json={"name": "Blocked Centre", "location": "Jamshedpur"},
    )
    assert forbidden.status_code == 403

    token = admin_token(client)
    centre = client.post(
        "/centres",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "City Diagnostics", "location": "Jamshedpur"},
    )
    test = client.post(
        "/tests",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "CBC", "description": "Complete blood count", "base_price": "450.00"},
    )
    assert centre.status_code == 201
    assert test.status_code == 201
    mapping = client.post(
        f"/centres/{centre.json()['id']}/tests",
        headers={"Authorization": f"Bearer {token}"},
        json={"test_id": test.json()["id"], "price": "475.00"},
    )
    assert mapping.status_code == 201


def prepare_booking(client):
    patient_token = login(client) if signup(client).status_code == 201 else login(client)
    token_admin = admin_token(client)
    centre = client.post(
        "/centres",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"name": "Booking Centre", "location": "Adityapur"},
    ).json()
    test = client.post(
        "/tests",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"name": "Lipid Panel", "description": "Lipid profile", "base_price": "650.00"},
    ).json()
    client.post(
        f"/centres/{centre['id']}/tests",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"test_id": test["id"], "price": "699.00"},
    )
    appointment = (datetime.now(UTC) + timedelta(days=1)).replace(microsecond=0)
    booking = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {patient_token}"},
        json={"centre_id": centre["id"], "test_id": test["id"], "appointment_at": appointment.isoformat()},
    )
    return patient_token, booking.json()


def test_booking_and_payment_idempotency(client):
    token, booking = prepare_booking(client)
    assert booking["status"] == "PENDING"

    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "pay-key-1"}
    payment = client.post(
        "/payments/",
        headers=headers,
        json={"booking_id": booking["id"], "simulate_status": "SUCCESS"},
    )
    duplicate = client.post(
        "/payments/",
        headers=headers,
        json={"booking_id": booking["id"], "simulate_status": "FAILED"},
    )
    assert payment.status_code == 201
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == payment.json()["id"]


def test_webhook_is_idempotent_and_does_not_duplicate(client):
    token, booking = prepare_booking(client)
    payment = client.post(
        "/payments/",
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "pay-key-webhook"},
        json={"booking_id": booking["id"], "simulate_status": "SUCCESS"},
    ).json()
    payload = {
        "event_id": "evt_123",
        "payment_id": payment["id"],
        "event_type": "payment.updated",
        "status": "SUCCESS",
    }
    headers = {"X-Webhook-Secret": "dev-webhook-secret"}
    first = client.post("/payments/webhook/", headers=headers, json=payload)
    second = client.post("/payments/webhook/", headers=headers, json=payload)
    assert first.status_code == 200
    assert first.json()["processed"] is True
    assert second.status_code == 200
    assert second.json()["processed"] is False


def test_admin_webhook_demo_helper_uses_same_idempotency_logic(client):
    token, booking = prepare_booking(client)
    payment = client.post(
        "/payments/",
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "pay-demo-helper"},
        json={"booking_id": booking["id"], "simulate_status": "SUCCESS"},
    ).json()
    admin = admin_token(client)
    payload = {
        "event_id": "evt-demo-helper",
        "payment_id": payment["id"],
        "event_type": "payment.updated",
        "status": "SUCCESS",
    }
    first = client.post("/payments/webhook/demo/", headers={"Authorization": f"Bearer {admin}"}, json=payload)
    second = client.post("/payments/webhook/demo/", headers={"Authorization": f"Bearer {admin}"}, json=payload)
    assert first.status_code == 200
    assert first.json()["processed"] is True
    assert second.status_code == 200
    assert second.json()["processed"] is False


def test_unauthorized_booking_and_invalid_booking(client):
    token_a = login(client, "a@example.com") if signup(client, "a@example.com").status_code == 201 else login(client, "a@example.com")
    signup(client, "b@example.com")
    token_b = login(client, "b@example.com")
    missing = client.get("/bookings/99999", headers={"Authorization": f"Bearer {token_a}"})
    assert missing.status_code == 404

    # No booking exists yet, so access control is exercised with a known booking below.
    token_admin = admin_token(client)
    centre = client.post(
        "/centres",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"name": "Auth Centre", "location": "Bistupur"},
    ).json()
    test = client.post(
        "/tests",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"name": "HbA1c", "description": "Average glucose marker", "base_price": "500.00"},
    ).json()
    client.post(
        f"/centres/{centre['id']}/tests",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"test_id": test["id"], "price": "500.00"},
    )
    booking = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "centre_id": centre["id"],
            "test_id": test["id"],
            "appointment_at": (datetime.now(UTC) + timedelta(days=2)).replace(microsecond=0).isoformat(),
        },
    ).json()
    denied = client.get(f"/bookings/{booking['id']}", headers={"Authorization": f"Bearer {token_b}"})
    assert denied.status_code == 403
