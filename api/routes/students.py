from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth import get_current_user_id
from api.database import get_db
from api.models.alumno import Alumno
from api.schemas.alumno import AlumnoCreate, AlumnoRead, AlumnoUpdate

router = APIRouter(prefix="/alumnos", tags=["alumnos"])


@router.get("/", response_model=list[AlumnoRead])
def listar(
    educational_center_id: str | None = None,
    group_id: str | None = None,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    q = db.query(Alumno).filter(Alumno.user_id == uid)
    if educational_center_id:
        q = q.filter(Alumno.educational_center_id == educational_center_id)
    if group_id:
        q = q.filter(Alumno.group_id == group_id)
    return q.order_by(Alumno.nombre_completo).all()


@router.post("/", response_model=AlumnoRead, status_code=201)
def crear(data: AlumnoCreate, uid: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    a = Alumno(**data.model_dump(), user_id=uid)
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@router.get("/{alumno_id}", response_model=AlumnoRead)
def obtener(alumno_id: int, uid: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    a = db.query(Alumno).filter(Alumno.id == alumno_id, Alumno.user_id == uid).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")
    return a


@router.put("/{alumno_id}", response_model=AlumnoRead)
def actualizar(alumno_id: int, data: AlumnoUpdate, uid: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    a = db.query(Alumno).filter(Alumno.id == alumno_id, Alumno.user_id == uid).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(a, field, value)
    db.commit()
    db.refresh(a)
    return a


@router.delete("/{alumno_id}", status_code=204)
def eliminar(alumno_id: int, uid: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    a = db.query(Alumno).filter(Alumno.id == alumno_id, Alumno.user_id == uid).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")
    db.delete(a)
    db.commit()
