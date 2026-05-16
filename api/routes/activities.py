import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth import get_current_user_id
from api.database import get_db
from api.models.activity import Activity
from api.models.activity_sequence import ActivitySequence
from api.models.group import Group
from api.models.integrative_project import IntegrativeProject
from api.schemas.activity import ActivityCreate, ActivityRead, ActivityUpdate

router = APIRouter(tags=["activities"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_agent_content(raw_content: str | None, activity: Activity) -> None:
    """
    Detecta el tipo de JSON generado por el agente (planificacion o secuencia)
    y puebla los campos estructurados del modelo Activity.

    Tipo 'planificacion' — tiene clave 'momentos'
    Tipo 'secuencia'     — tiene clave 'actividades'
    """
    if not raw_content:
        return

    try:
        data = json.loads(raw_content)
    except (json.JSONDecodeError, TypeError):
        return

    if not isinstance(data, dict):
        return

    if "momentos" in data:
        # planificacion — los campos raíz mapean directo
        activity.activity_type = "planificacion"
        activity.curriculum_space = data.get("espacio") or activity.curriculum_space
        activity.curriculum_unit = data.get("unidad") or activity.curriculum_unit
        stage_val = data.get("tramo")
        if stage_val is not None:
            try:
                activity.stage = int(stage_val)
            except (ValueError, TypeError):
                pass
        activity.specific_competency_code = data.get("ce_codigo") or activity.specific_competency_code
        activity.specific_competency = data.get("ce_texto") or activity.specific_competency
        activity.curriculum_content = data.get("contenido") or activity.curriculum_content
        activity.achievement_criterion = data.get("criterio_de_logro") or activity.achievement_criterion
        activity.methodology = data.get("metodologia") or activity.methodology

        # meta_aprendizaje viene del momento Inicio
        momentos = data.get("momentos", [])
        for momento in momentos:
            if isinstance(momento, dict):
                meta = momento.get("meta_aprendizaje")
                if meta:
                    activity.learning_goal = meta
                    break

        # competencias_mcn → JSON array string
        competencias = data.get("competencias_mcn")
        if competencias is not None:
            activity.general_competencies = (
                json.dumps(competencias) if not isinstance(competencias, str) else competencias
            )

    elif "actividades" in data:
        # secuencia — los campos raíz mapean con nombres distintos
        activity.activity_type = "secuencia"
        activity.curriculum_space = data.get("espacio") or activity.curriculum_space
        activity.curriculum_unit = data.get("unidad_curricular") or activity.curriculum_unit
        activity.learning_goal = data.get("meta_aprendizaje") or activity.learning_goal

        # criterios_de_logro[] → join con coma
        criterios = data.get("criterios_de_logro")
        if criterios and isinstance(criterios, list):
            activity.achievement_criterion = ", ".join(str(c) for c in criterios)
        elif criterios and isinstance(criterios, str):
            activity.achievement_criterion = criterios

        # competencias_generales[] → JSON array string
        competencias = data.get("competencias_generales")
        if competencias is not None:
            activity.general_competencies = (
                json.dumps(competencias) if not isinstance(competencias, str) else competencias
            )


def _verify_project_ownership(
    group_id: str, project_id: str, user_id: str, db: Session
) -> IntegrativeProject:
    """Verifica group → project ownership. Lanza 404 si algo falla."""
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


def _verify_sequence_ownership(
    group_id: str, project_id: str, sequence_id: str, user_id: str, db: Session
) -> ActivitySequence:
    """Verifica group → project → sequence ownership. Lanza 404 si algo falla."""
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


def _get_activity_or_404(activity_id: str, user_id: str, db: Session) -> Activity:
    """Verifica ownership de la actividad via user_id denormalizado. Lanza 404 si no existe o no es del usuario."""
    activity = (
        db.query(Activity)
        .filter(Activity.id == activity_id, Activity.user_id == user_id)
        .first()
    )
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


# ---------------------------------------------------------------------------
# 1. Project-level activities
# ---------------------------------------------------------------------------

@router.get(
    "/groups/{group_id}/projects/{project_id}/activities/",
    response_model=list[ActivityRead],
)
def list_project_activities(
    group_id: str,
    project_id: str,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _verify_project_ownership(group_id, project_id, uid, db)
    return (
        db.query(Activity)
        .filter(
            Activity.project_id == project_id,
            Activity.user_id == uid,
        )
        .order_by(Activity.order, Activity.created_at)
        .all()
    )


@router.post(
    "/groups/{group_id}/projects/{project_id}/activities/",
    response_model=ActivityRead,
    status_code=201,
)
def create_project_activity(
    group_id: str,
    project_id: str,
    data: ActivityCreate,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _verify_project_ownership(group_id, project_id, uid, db)
    payload = data.model_dump()
    # Sobreescribir FKs con los del path para garantizar integridad
    payload["project_id"] = project_id
    payload["group_id"] = group_id
    activity = Activity(**payload, user_id=uid)
    _parse_agent_content(activity.raw_content, activity)
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


# ---------------------------------------------------------------------------
# 2. Sequence-level activities
# ---------------------------------------------------------------------------

@router.get(
    "/groups/{group_id}/projects/{project_id}/sequences/{sequence_id}/activities/",
    response_model=list[ActivityRead],
)
def list_sequence_activities(
    group_id: str,
    project_id: str,
    sequence_id: str,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _verify_sequence_ownership(group_id, project_id, sequence_id, uid, db)
    return (
        db.query(Activity)
        .filter(
            Activity.sequence_id == sequence_id,
            Activity.user_id == uid,
        )
        .order_by(Activity.order, Activity.created_at)
        .all()
    )


@router.post(
    "/groups/{group_id}/projects/{project_id}/sequences/{sequence_id}/activities/",
    response_model=ActivityRead,
    status_code=201,
)
def create_sequence_activity(
    group_id: str,
    project_id: str,
    sequence_id: str,
    data: ActivityCreate,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _verify_sequence_ownership(group_id, project_id, sequence_id, uid, db)
    payload = data.model_dump()
    # Sobreescribir FKs con los del path para garantizar integridad
    payload["project_id"] = project_id
    payload["sequence_id"] = sequence_id
    payload["group_id"] = group_id
    activity = Activity(**payload, user_id=uid)
    _parse_agent_content(activity.raw_content, activity)
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


# ---------------------------------------------------------------------------
# 3. Individual activity (ownership via denormalized user_id)
# ---------------------------------------------------------------------------

@router.get("/activities/{activity_id}", response_model=ActivityRead)
def get_activity(
    activity_id: str,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return _get_activity_or_404(activity_id, uid, db)


@router.patch("/activities/{activity_id}", response_model=ActivityRead)
def update_activity(
    activity_id: str,
    data: ActivityUpdate,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    activity = _get_activity_or_404(activity_id, uid, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(activity, field, value)
    db.commit()
    db.refresh(activity)
    return activity


@router.delete("/activities/{activity_id}", status_code=204)
def delete_activity(
    activity_id: str,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    activity = _get_activity_or_404(activity_id, uid, db)
    db.delete(activity)
    db.commit()


# ---------------------------------------------------------------------------
# 4. Orphaned creation (backward compat con agente)
#    Crea actividad con todos los FKs en NULL (o los que venga en el body)
# ---------------------------------------------------------------------------

@router.post("/activities/", response_model=ActivityRead, status_code=201)
def create_orphan_activity(
    data: ActivityCreate,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Crea una actividad sin jerarquía obligatoria — compatible con el agente IA existente."""
    activity = Activity(**data.model_dump(), user_id=uid)
    _parse_agent_content(activity.raw_content, activity)
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity
