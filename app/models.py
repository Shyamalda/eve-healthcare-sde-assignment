from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="PATIENT", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")


class DiagnosticCentre(Base):
    __tablename__ = "diagnostic_centres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tests: Mapped[list["CentreTest"]] = relationship(back_populates="centre", cascade="all, delete-orphan")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="centre")


class DiagnosticTest(Base):
    __tablename__ = "diagnostic_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    centres: Mapped[list["CentreTest"]] = relationship(back_populates="test", cascade="all, delete-orphan")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="test")


class CentreTest(Base):
    __tablename__ = "centre_tests"
    __table_args__ = (UniqueConstraint("centre_id", "test_id", name="uq_centre_test"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    centre_id: Mapped[int] = mapped_column(ForeignKey("diagnostic_centres.id", ondelete="CASCADE"), nullable=False)
    test_id: Mapped[int] = mapped_column(ForeignKey("diagnostic_tests.id", ondelete="CASCADE"), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    centre: Mapped[DiagnosticCentre] = relationship(back_populates="tests")
    test: Mapped[DiagnosticTest] = relationship(back_populates="centres")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("diagnostic_tests.id", ondelete="RESTRICT"), nullable=False)
    centre_id: Mapped[int] = mapped_column(ForeignKey("diagnostic_centres.id", ondelete="RESTRICT"), nullable=False)
    appointment_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="bookings")
    test: Mapped[DiagnosticTest] = relationship(back_populates="bookings")
    centre: Mapped[DiagnosticCentre] = relationship(back_populates="bookings")
    payment: Mapped["Payment | None"] = relationship(back_populates="booking", uselist=False, cascade="all, delete-orphan")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    provider_payment_id: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    booking: Mapped[Booking] = relationship(back_populates="payment")
    webhook_events: Mapped[list["WebhookEvent"]] = relationship(back_populates="payment")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    payment: Mapped[Payment] = relationship(back_populates="webhook_events")
