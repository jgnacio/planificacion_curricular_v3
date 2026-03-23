from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.planificacion import Planificacion
from api.schemas.planificacion import PlanificacionCreate, PlanificacionRead, PlanificacionUpdate

router = APIRouter(prefix="/planificaciones", tags=["planificaciones"])


@router.get("/", response_model=list[PlanificacionRead])
def listar(db: Session = Depends(get_db)):
    return db.query(Planificacion).order_by(Planificacion.created_at.desc()).all()


@router.post("/", response_model=PlanificacionRead, status_code=201)
def crear(data: PlanificacionCreate, db: Session = Depends(get_db)):
    p = Planificacion(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.get("/{planificacion_id}", response_model=PlanificacionRead)
def obtener(planificacion_id: int, db: Session = Depends(get_db)):
    p = db.get(Planificacion, planificacion_id)
    if not p:
        raise HTTPException(status_code=404, detail="Planificación no encontrada")
    return p


@router.put("/{planificacion_id}", response_model=PlanificacionRead)
def actualizar(planificacion_id: int, data: PlanificacionUpdate, db: Session = Depends(get_db)):
    p = db.get(Planificacion, planificacion_id)
    if not p:
        raise HTTPException(status_code=404, detail="Planificación no encontrada")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{planificacion_id}", status_code=204)
def eliminar(planificacion_id: int, db: Session = Depends(get_db)):
    p = db.get(Planificacion, planificacion_id)
    if not p:
        raise HTTPException(status_code=404, detail="Planificación no encontrada")
    db.delete(p)
    db.commit()
