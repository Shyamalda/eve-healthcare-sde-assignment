from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Booking, Payment, User
from ..schemas import PaymentCreate, PaymentResponse, PaymentWebhook, WebhookResponse
from ..security import get_current_user, require_admin
from ..services.payment_service import PaymentConflict, create_mock_payment, process_webhook

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Payment:
    booking = db.get(Booking, payload.booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="You are not authorized to pay for this booking")
    if idempotency_key and len(idempotency_key) > 120:
        raise HTTPException(status_code=422, detail="Idempotency-Key must be 120 characters or fewer")

    try:
        payment = create_mock_payment(db, booking, idempotency_key, payload.simulate_status)
        db.commit()
    except PaymentConflict as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.refresh(payment)
    return payment


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Payment:
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.booking.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="You are not authorized to access this payment")
    return payment


@router.post("/webhook/", response_model=WebhookResponse)
def payment_webhook(
    payload: PaymentWebhook,
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
    db: Session = Depends(get_db),
) -> WebhookResponse:
    if x_webhook_secret != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    try:
        event, payment, booking, processed = process_webhook(db, payload)
        db.commit()
    except PaymentConflict as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return WebhookResponse(
        event_id=event.event_id,
        processed=processed,
        payment_id=payment.id,
        payment_status=payment.status,
        booking_id=booking.id,
        booking_status=booking.status,
    )


@router.post("/webhook/demo/", response_model=WebhookResponse)
def payment_webhook_demo(
    payload: PaymentWebhook,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> WebhookResponse:
    """Authenticated demo helper for the web UI; the real provider endpoint remains /payments/webhook/."""
    try:
        event, payment, booking, processed = process_webhook(db, payload)
        db.commit()
    except PaymentConflict as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return WebhookResponse(
        event_id=event.event_id,
        processed=processed,
        payment_id=payment.id,
        payment_status=payment.status,
        booking_id=booking.id,
        booking_status=booking.status,
    )
