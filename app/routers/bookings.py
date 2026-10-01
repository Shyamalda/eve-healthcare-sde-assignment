from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Booking, CentreTest, DiagnosticCentre, DiagnosticTest, User
from ..schemas import BookingCreate, BookingResponse, BookingStatus
from ..security import get_current_user

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Booking:
    centre = db.scalar(select(DiagnosticCentre).where(DiagnosticCentre.id == payload.centre_id, DiagnosticCentre.is_active.is_(True)))
    test = db.scalar(select(DiagnosticTest).where(DiagnosticTest.id == payload.test_id, DiagnosticTest.is_active.is_(True)))
    if not centre:
        raise HTTPException(status_code=404, detail="Diagnostic centre not found")
    if not test:
        raise HTTPException(status_code=404, detail="Diagnostic test not found")

    mapping = db.scalar(
        select(CentreTest).where(
            CentreTest.centre_id == payload.centre_id,
            CentreTest.test_id == payload.test_id,
            CentreTest.is_active.is_(True),
        )
    )
    if not mapping:
        raise HTTPException(status_code=409, detail="This diagnostic test is not available at the selected centre")

    booking = Booking(
        user_id=current_user.id,
        test_id=test.id,
        centre_id=centre.id,
        appointment_at=payload.appointment_at,
        amount=mapping.price,
        status=BookingStatus.PENDING.value,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/me", response_model=list[BookingResponse])
def my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Booking]:
    return list(
        db.scalars(
            select(Booking).where(Booking.user_id == current_user.id).order_by(Booking.created_at.desc())
        )
    )


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Booking:
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="You are not authorized to access this booking")
    return booking


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Booking:
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="You are not authorized to modify this booking")
    if booking.status != BookingStatus.PENDING.value:
        raise HTTPException(status_code=409, detail=f"Only pending bookings can be cancelled; current status is {booking.status}")
    booking.status = BookingStatus.CANCELLED.value
    db.commit()
    db.refresh(booking)
    return booking
