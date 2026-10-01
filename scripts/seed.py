from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import CentreTest, DiagnosticCentre, DiagnosticTest, User
from app.security import hash_password


ADMIN_EMAIL = "admin@evehealthcare.local"
ADMIN_PASSWORD = "Admin@12345"
DEMO_EMAIL = "demo@evehealthcare.local"
DEMO_PASSWORD = "Demo@12345"


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
        if not admin:
            db.add(User(name="EVE Admin", email=ADMIN_EMAIL, password_hash=hash_password(ADMIN_PASSWORD), role="ADMIN"))

        demo_patient = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if not demo_patient:
            db.add(User(name="Demo Patient", email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD), role="PATIENT"))

        tests = [
            ("Complete Blood Count", "CBC test for common blood parameters.", Decimal("450.00")),
            ("Lipid Profile", "Cholesterol and triglyceride assessment.", Decimal("650.00")),
            ("HbA1c", "Three-month average blood glucose marker.", Decimal("500.00")),
        ]
        test_rows: list[DiagnosticTest] = []
        for name, description, price in tests:
            row = db.scalar(select(DiagnosticTest).where(DiagnosticTest.name == name))
            if not row:
                row = DiagnosticTest(name=name, description=description, base_price=price)
                db.add(row)
                db.flush()
            test_rows.append(row)

        centres = [
            ("EVE Central Diagnostics", "Sakchi, Jamshedpur"),
            ("EVE Care Lab", "Bistupur, Jamshedpur"),
        ]
        centre_rows: list[DiagnosticCentre] = []
        for name, location in centres:
            row = db.scalar(select(DiagnosticCentre).where(DiagnosticCentre.name == name))
            if not row:
                row = DiagnosticCentre(name=name, location=location)
                db.add(row)
                db.flush()
            centre_rows.append(row)

        for centre in centre_rows:
            for test in test_rows:
                exists = db.scalar(select(CentreTest).where(CentreTest.centre_id == centre.id, CentreTest.test_id == test.id))
                if not exists:
                    db.add(CentreTest(centre_id=centre.id, test_id=test.id, price=test.base_price))

        db.commit()
        print(f"Seed complete. Admin: {ADMIN_EMAIL} / {ADMIN_PASSWORD} | Demo patient: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
