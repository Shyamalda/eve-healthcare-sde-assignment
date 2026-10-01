from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CentreTest, DiagnosticCentre, DiagnosticTest
from ..schemas import CentreCreate, CentreResponse, CentreTestAttach, CentreTestResponse, CentreUpdate
from ..security import require_admin

router = APIRouter(prefix="/centres", tags=["Diagnostic Centres"])


@router.get("", response_model=list[CentreResponse])
def list_centres(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[DiagnosticCentre]:
    offset = (page - 1) * page_size
    return list(
        db.scalars(
            select(DiagnosticCentre)
            .where(DiagnosticCentre.is_active.is_(True))
            .order_by(DiagnosticCentre.name)
            .offset(offset)
            .limit(page_size)
        )
    )


@router.post("", response_model=CentreResponse, status_code=status.HTTP_201_CREATED)
def create_centre(
    payload: CentreCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
) -> DiagnosticCentre:
    centre = DiagnosticCentre(name=payload.name.strip(), location=payload.location.strip())
    db.add(centre)
    db.commit()
    db.refresh(centre)
    return centre


@router.get("/{centre_id}", response_model=CentreResponse)
def get_centre(centre_id: int, db: Session = Depends(get_db)) -> DiagnosticCentre:
    centre = db.scalar(select(DiagnosticCentre).where(DiagnosticCentre.id == centre_id, DiagnosticCentre.is_active.is_(True)))
    if not centre:
        raise HTTPException(status_code=404, detail="Diagnostic centre not found")
    return centre


@router.patch("/{centre_id}", response_model=CentreResponse)
def update_centre(
    centre_id: int,
    payload: CentreUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
) -> DiagnosticCentre:
    centre = db.get(DiagnosticCentre, centre_id)
    if not centre:
        raise HTTPException(status_code=404, detail="Diagnostic centre not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(centre, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(centre)
    return centre


@router.delete("/{centre_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_centre(
    centre_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
) -> None:
    centre = db.get(DiagnosticCentre, centre_id)
    if not centre:
        raise HTTPException(status_code=404, detail="Diagnostic centre not found")
    centre.is_active = False
    db.commit()


@router.get("/{centre_id}/tests", response_model=list[CentreTestResponse])
def list_centre_tests(centre_id: int, db: Session = Depends(get_db)) -> list[CentreTest]:
    centre = db.get(DiagnosticCentre, centre_id)
    if not centre or not centre.is_active:
        raise HTTPException(status_code=404, detail="Diagnostic centre not found")
    return list(
        db.scalars(
            select(CentreTest)
            .where(CentreTest.centre_id == centre_id, CentreTest.is_active.is_(True))
            .order_by(CentreTest.id)
        )
    )


@router.post("/{centre_id}/tests", response_model=CentreTestResponse, status_code=status.HTTP_201_CREATED)
def attach_test(
    centre_id: int,
    payload: CentreTestAttach,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
) -> CentreTest:
    centre = db.get(DiagnosticCentre, centre_id)
    test = db.get(DiagnosticTest, payload.test_id)
    if not centre or not centre.is_active:
        raise HTTPException(status_code=404, detail="Diagnostic centre not found")
    if not test or not test.is_active:
        raise HTTPException(status_code=404, detail="Diagnostic test not found")
    existing = db.scalar(select(CentreTest).where(CentreTest.centre_id == centre_id, CentreTest.test_id == payload.test_id))
    if existing:
        if existing.is_active:
            raise HTTPException(status_code=409, detail="Test is already offered by this centre")
        existing.price = payload.price
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return existing
    mapping = CentreTest(centre_id=centre_id, test_id=payload.test_id, price=payload.price)
    db.add(mapping)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Test is already offered by this centre") from None
    db.refresh(mapping)
    return mapping


@router.delete("/{centre_id}/tests/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
def detach_test(
    centre_id: int,
    test_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
) -> None:
    mapping = db.scalar(select(CentreTest).where(CentreTest.centre_id == centre_id, CentreTest.test_id == test_id))
    if not mapping:
        raise HTTPException(status_code=404, detail="Centre/test mapping not found")
    mapping.is_active = False
    db.commit()
