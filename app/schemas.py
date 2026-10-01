from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Role(StrEnum):
    PATIENT = "PATIENT"
    ADMIN = "ADMIN"


class BookingStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Enter a valid email address")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: Role


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CentreCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    location: str = Field(min_length=2, max_length=255)


class CentreUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    location: str | None = Field(default=None, min_length=2, max_length=255)
    is_active: bool | None = None


class TestCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    base_price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class TestUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    base_price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    is_active: bool | None = None


class CentreTestAttach(BaseModel):
    test_id: int = Field(gt=0)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class CentreTestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    centre_id: int
    test_id: int
    price: Decimal
    is_active: bool


class CentreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str
    is_active: bool


class TestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    base_price: Decimal
    is_active: bool


class BookingCreate(BaseModel):
    test_id: int = Field(gt=0)
    centre_id: int = Field(gt=0)
    appointment_at: datetime

    @field_validator("appointment_at")
    @classmethod
    def appointment_must_be_future(cls, value: datetime) -> datetime:
        from datetime import UTC

        normalized = value if value.tzinfo else value.replace(tzinfo=UTC)
        if normalized <= datetime.now(UTC):
            raise ValueError("Appointment time must be in the future")
        return normalized


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    test_id: int
    centre_id: int
    appointment_at: datetime
    amount: Decimal
    status: BookingStatus


class PaymentCreate(BaseModel):
    booking_id: int = Field(gt=0)
    simulate_status: PaymentStatus | None = None


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    provider_payment_id: str
    amount: Decimal
    status: PaymentStatus


class PaymentWebhook(BaseModel):
    event_id: str = Field(min_length=3, max_length=120)
    payment_id: int = Field(gt=0)
    event_type: str = Field(min_length=2, max_length=80)
    status: PaymentStatus


class WebhookResponse(BaseModel):
    event_id: str
    processed: bool
    payment_id: int
    payment_status: PaymentStatus
    booking_id: int
    booking_status: BookingStatus
