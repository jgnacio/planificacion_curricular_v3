from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth import UserContext, get_current_user
from api.database import get_db
from api.models.educational_center import EducationalCenter
from api.schemas.educational_center import (
    EducationalCenterCreate,
    EducationalCenterRead,
    EducationalCenterUpdate,
)

router = APIRouter(prefix="/educational-centers", tags=["educational-centers"])


@router.get("/", response_model=list[EducationalCenterRead])
def list_centers(
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(EducationalCenter).filter(
        EducationalCenter.user_id == user.user_id
    ).order_by(EducationalCenter.name).all()


@router.post("/", response_model=EducationalCenterRead, status_code=201)
def create_center(
    data: EducationalCenterCreate,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    center = EducationalCenter(**data.model_dump(), user_id=user.user_id)
    db.add(center)
    db.commit()
    db.refresh(center)
    return center


@router.get("/{center_id}", response_model=EducationalCenterRead)
def get_center(
    center_id: str,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    center = _get_or_404(center_id, user.user_id, db)
    return center


@router.patch("/{center_id}", response_model=EducationalCenterRead)
def update_center(
    center_id: str,
    data: EducationalCenterUpdate,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    center = _get_or_404(center_id, user.user_id, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(center, field, value)
    db.commit()
    db.refresh(center)
    return center


@router.delete("/{center_id}", status_code=204)
def delete_center(
    center_id: str,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    center = _get_or_404(center_id, user.user_id, db)
    db.delete(center)
    db.commit()


def _get_or_404(center_id: str, user_id: str, db: Session) -> EducationalCenter:
    center = db.query(EducationalCenter).filter(
        EducationalCenter.id == center_id,
        EducationalCenter.user_id == user_id,
    ).first()
    if not center:
        raise HTTPException(status_code=404, detail="Educational center not found")
    return center
