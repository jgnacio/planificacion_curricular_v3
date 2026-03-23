from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.alumno import Alumno
from api.schemas.alumno import AlumnoCreate, AlumnoRead, AlumnoUpdate

router = APIRouter(prefix="/alumnos", tags=["alumnos"])


@router.get("/", response_model=list[AlumnoRead])
def listar(db: Session = Depends(get_db)):
    return db.query(Alumno).order_by(Alumno.nombre_completo).all()


@router.post("/", response_model=AlumnoRead, status_code=201)
def crear(data: AlumnoCreate, db: Session = Depends(get_db)):
    a = Alumno(**data.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@router.get("/{alumno_id}", response_model=AlumnoRead)
def obtener(alumno_id: int, db: Session = Depends(get_db)):
    a = db.get(Alumno, alumno_id)
    if not a:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")
    return a


@router.put("/{alumno_id}", response_model=AlumnoRead)
def actualizar(alumno_id: int, data: AlumnoUpdate, db: Session = Depends(get_db)):
    a = db.get(Alumno, alumno_id)
    if not a:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(a, field, value)
    db.commit()
    db.refresh(a)
    return a


@router.delete("/{alumno_id}", status_code=204)
def eliminar(alumno_id: int, db: Session = Depends(get_db)):
    a = db.get(Alumno, alumno_id)
    if not a:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")
    db.delete(a)
    db.commit()
