from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import Booking, Payment, WebhookEvent
from ..schemas import BookingStatus, PaymentStatus


class PaymentConflict(Exception):
    pass


def generate_provider_payment_id() -> str:
    return f"mockpay_{secrets.token_urlsafe(12)}"


def apply_payment_status(payment: Payment, booking: Booking, new_status: PaymentStatus) -> None:
    current = PaymentStatus(payment.status)

    # Payment states are intentionally monotonic once a terminal state is reached.
    # This prevents delayed/out-of-order webhook events from corrupting booking state.
    if current in (PaymentStatus.SUCCESS, PaymentStatus.FAILED):
        return

    payment.status = new_status.value
    if new_status == PaymentStatus.SUCCESS:
        booking.status = BookingStatus.CONFIRMED.value
    elif new_status == PaymentStatus.FAILED:
        booking.status = BookingStatus.FAILED.value


def create_mock_payment(
    db: Session,
    booking: Booking,
    idempotency_key: str | None,
    forced_status: PaymentStatus | None,
) -> Payment:
    if idempotency_key:
        existing = db.scalar(select(Payment).where(Payment.idempotency_key == idempotency_key))
        if existing:
            if existing.booking_id != booking.id:
                raise PaymentConflict("Idempotency key was already used for another booking")
            return existing

    existing_booking_payment = db.scalar(select(Payment).where(Payment.booking_id == booking.id))
    if existing_booking_payment:
        raise PaymentConflict("A payment already exists for this booking; use its existing idempotency key")

    if booking.status != BookingStatus.PENDING.value:
        raise PaymentConflict("Payment can only be initiated for a pending booking")

    payment = Payment(
        booking_id=booking.id,
        provider_payment_id=generate_provider_payment_id(),
        idempotency_key=idempotency_key,
        amount=booking.amount,
        status=PaymentStatus.PENDING.value,
    )
    db.add(payment)
    db.flush()

    outcome = forced_status or (PaymentStatus.SUCCESS if secrets.randbelow(100) < 85 else PaymentStatus.FAILED)
    apply_payment_status(payment, booking, outcome)
    db.flush()
    return payment


def process_webhook(db: Session, payload) -> tuple[WebhookEvent, Payment, Booking, bool]:
    existing_event = db.scalar(select(WebhookEvent).where(WebhookEvent.event_id == payload.event_id))
    if existing_event:
        payment = db.scalar(select(Payment).where(Payment.id == existing_event.payment_id))
        booking = payment.booking
        return existing_event, payment, booking, False

    payment = db.scalar(select(Payment).where(Payment.id == payload.payment_id))
    if not payment:
        raise PaymentConflict("Payment not found")

    booking = db.scalar(select(Booking).where(Booking.id == payment.booking_id).with_for_update())
    event = WebhookEvent(
        event_id=payload.event_id,
        payment_id=payment.id,
        event_type=payload.event_type,
    )
    db.add(event)
    apply_payment_status(payment, booking, payload.status)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing_event = db.scalar(select(WebhookEvent).where(WebhookEvent.event_id == payload.event_id))
        payment = db.scalar(select(Payment).where(Payment.id == existing_event.payment_id))
        return existing_event, payment, payment.booking, False

    return event, payment, booking, True
