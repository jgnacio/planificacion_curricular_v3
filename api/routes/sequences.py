from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth import get_current_user_id
from api.database import get_db
from api.dependencies import ensure_user_profile
from api.models.activity_sequence import ActivitySequence
from api.models.group import Group
from api.models.integrative_project import IntegrativeProject
from api.schemas.activity_sequence import (
    ActivitySequenceCreate,
    ActivitySequenceRead,
    ActivitySequenceUpdate,
)

router = APIRouter(prefix="/groups", tags=["sequences"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _verify_project_ownership(
    group_id: str, project_id: str, user_id: str, db: Session
) -> IntegrativeProject:
    """Verifica ownership del grupo y del proyecto. Lanza 404 si no existe o no pertenece al usuario."""
    group = (
        db.query(Group)
        .filter(Group.id == group_id, Group.user_id == user_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    project = (
        db.query(IntegrativeProject)
        .filter(
            IntegrativeProject.id == project_id,
            IntegrativeProject.group_id == group_id,
            IntegrativeProject.user_id == user_id,
        )
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Integrative project not found")

    return project


def _get_sequence_or_404(
    group_id: str, project_id: str, sequence_id: str, user_id: str, db: Session
) -> ActivitySequence:
    """Verifica la cadena group→project→sequence y lanza 404 si algo falla."""
    _verify_project_ownership(group_id, project_id, user_id, db)
    sequence = (
        db.query(ActivitySequence)
        .filter(
            ActivitySequence.id == sequence_id,
            ActivitySequence.project_id == project_id,
            ActivitySequence.user_id == user_id,
        )
        .first()
    )
    if not sequence:
        raise HTTPException(status_code=404, detail="Activity sequence not found")
    return sequence


# ---------------------------------------------------------------------------
# Sequences CRUD (nested under group/project)
# ---------------------------------------------------------------------------

@router.get(
    "/{group_id}/projects/{project_id}/sequences/",
    response_model=list[ActivitySequenceRead],
)
def list_sequences(
    group_id: str,
    project_id: str,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _verify_project_ownership(group_id, project_id, uid, db)
    return (
        db.query(ActivitySequence)
        .filter(ActivitySequence.project_id == project_id, ActivitySequence.user_id == uid)
        .order_by(ActivitySequence.order, ActivitySequence.created_at)
        .all()
    )


@router.post(
    "/{group_id}/projects/{project_id}/sequences/",
    response_model=ActivitySequenceRead,
    status_code=201,
)
def create_sequence(
    group_id: str,
    project_id: str,
    data: ActivitySequenceCreate,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    ensure_user_profile(uid, db)
    _verify_project_ownership(group_id, project_id, uid, db)
    payload = data.model_dump()
    # project_id viene del path — sobreescribir para garantizar integridad
    payload["project_id"] = project_id
    sequence = ActivitySequence(**payload, user_id=uid)
    db.add(sequence)
    db.commit()
    db.refresh(sequence)
    return sequence


@router.get(
    "/{group_id}/projects/{project_id}/sequences/{sequence_id}",
    response_model=ActivitySequenceRead,
)
def get_sequence(
    group_id: str,
    project_id: str,
    sequence_id: str,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return _get_sequence_or_404(group_id, project_id, sequence_id, uid, db)


@router.patch(
    "/{group_id}/projects/{project_id}/sequences/{sequence_id}",
    response_model=ActivitySequenceRead,
)
def update_sequence(
    group_id: str,
    project_id: str,
    sequence_id: str,
    data: ActivitySequenceUpdate,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    sequence = _get_sequence_or_404(group_id, project_id, sequence_id, uid, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(sequence, field, value)
    db.commit()
    db.refresh(sequence)
    return sequence


@router.delete(
    "/{group_id}/projects/{project_id}/sequences/{sequence_id}",
    status_code=204,
)
def delete_sequence(
    group_id: str,
    project_id: str,
    sequence_id: str,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    sequence = _get_sequence_or_404(group_id, project_id, sequence_id, uid, db)
    db.delete(sequence)
    db.commit()
