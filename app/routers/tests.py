from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import DiagnosticTest
from ..schemas import TestCreate, TestResponse, TestUpdate
from ..security import require_admin

router = APIRouter(prefix="/tests", tags=["Diagnostic Tests"])


@router.get("", response_model=list[TestResponse])
def list_tests(db: Session = Depends(get_db)) -> list[DiagnosticTest]:
    return list(db.scalars(select(DiagnosticTest).where(DiagnosticTest.is_active.is_(True)).order_by(DiagnosticTest.name)))


@router.post("", response_model=TestResponse, status_code=status.HTTP_201_CREATED)
def create_test(
    payload: TestCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
) -> DiagnosticTest:
    test = DiagnosticTest(
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        base_price=payload.base_price,
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    return test


@router.get("/{test_id}", response_model=TestResponse)
def get_test(test_id: int, db: Session = Depends(get_db)) -> DiagnosticTest:
    test = db.scalar(select(DiagnosticTest).where(DiagnosticTest.id == test_id, DiagnosticTest.is_active.is_(True)))
    if not test:
        raise HTTPException(status_code=404, detail="Diagnostic test not found")
    return test


@router.patch("/{test_id}", response_model=TestResponse)
def update_test(
    test_id: int,
    payload: TestUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
) -> DiagnosticTest:
    test = db.get(DiagnosticTest, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Diagnostic test not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(test, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(test)
    return test


@router.delete("/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_test(
    test_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
) -> None:
    test = db.get(DiagnosticTest, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Diagnostic test not found")
    test.is_active = False
    db.commit()
