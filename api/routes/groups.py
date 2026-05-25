import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth import get_current_user_id
from api.database import get_db
from api.dependencies import ensure_user_profile
from api.models.alumno import Alumno
from api.models.group import Group
from api.models.integrative_project import IntegrativeProject
from api.schemas.alumno import AlumnoRead
from api.schemas.group import GroupCreate, GroupRead, GroupUpdate
from api.schemas.integrative_project import (
    IntegrativeProjectCreate,
    IntegrativeProjectRead,
    IntegrativeProjectUpdate,
)

router = APIRouter(prefix="/groups", tags=["groups"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_group_or_404(group_id: str, user_id: str, db: Session) -> Group:
    """Devuelve el grupo del usuario o lanza 404 (nunca 403)."""
    group = (
        db.query(Group)
        .filter(Group.id == group_id, Group.user_id == user_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


def _get_project_or_404(
    group_id: str, project_id: str, user_id: str, db: Session
) -> IntegrativeProject:
    """Verifica ownership del grupo y luego devuelve el proyecto o lanza 404."""
    _get_group_or_404(group_id, user_id, db)
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


def _serialize_project_lists(data: dict) -> dict:
    """Serializa listas a JSON string para almacenar en DB."""
    for field in ("curriculum_space_ids", "competency_ids"):
        if field in data and isinstance(data[field], list):
            data[field] = json.dumps(data[field])
    return data


# ---------------------------------------------------------------------------
# Groups CRUD
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[GroupRead])
def list_groups(
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return (
        db.query(Group)
        .filter(Group.user_id == uid)
        .order_by(Group.created_at.desc())
        .all()
    )


@router.post("/", response_model=GroupRead, status_code=201)
def create_group(
    data: GroupCreate,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    ensure_user_profile(uid, db)
    group = Group(**data.model_dump(), user_id=uid)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.get("/{group_id}", response_model=GroupRead)
def get_group(
    group_id: str,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return _get_group_or_404(group_id, uid, db)


@router.patch("/{group_id}", response_model=GroupRead)
def update_group(
    group_id: str,
    data: GroupUpdate,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    group = _get_group_or_404(group_id, uid, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(group, field, value)
    db.commit()
    db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=204)
def delete_group(
    group_id: str,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    group = _get_group_or_404(group_id, uid, db)
    db.delete(group)
    db.commit()


# ---------------------------------------------------------------------------
# Nested: Integrative Projects within a Group
# ---------------------------------------------------------------------------

@router.get("/{group_id}/projects/", response_model=list[IntegrativeProjectRead])
def list_projects(
    group_id: str,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _get_group_or_404(group_id, uid, db)
    return (
        db.query(IntegrativeProject)
        .filter(
            IntegrativeProject.group_id == group_id,
            IntegrativeProject.user_id == uid,
        )
        .order_by(IntegrativeProject.created_at.desc())
        .all()
    )


@router.post("/{group_id}/projects/", response_model=IntegrativeProjectRead, status_code=201)
def create_project(
    group_id: str,
    data: IntegrativeProjectCreate,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    ensure_user_profile(uid, db)
    _get_group_or_404(group_id, uid, db)
    payload = data.model_dump()
    # group_id viene del path — sobreescribir para garantizar integridad
    payload["group_id"] = group_id
    payload = _serialize_project_lists(payload)
    project = IntegrativeProject(**payload, user_id=uid)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{group_id}/projects/{project_id}", response_model=IntegrativeProjectRead)
def get_project(
    group_id: str,
    project_id: str,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return _get_project_or_404(group_id, project_id, uid, db)


@router.patch("/{group_id}/projects/{project_id}", response_model=IntegrativeProjectRead)
def update_project(
    group_id: str,
    project_id: str,
    data: IntegrativeProjectUpdate,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(group_id, project_id, uid, db)
    payload = _serialize_project_lists(data.model_dump(exclude_unset=True))
    for field, value in payload.items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{group_id}/projects/{project_id}", status_code=204)
def delete_project(
    group_id: str,
    project_id: str,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(group_id, project_id, uid, db)
    db.delete(project)
    db.commit()


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------

@router.get("/{group_id}/students/", response_model=list[AlumnoRead])
def list_students(
    group_id: str,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _get_group_or_404(group_id, uid, db)
    return (
        db.query(Alumno)
        .filter(Alumno.group_id == group_id, Alumno.user_id == uid)
        .order_by(Alumno.nombre_completo)
        .all()
    )


