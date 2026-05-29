from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth import get_current_user_id
from api.database import get_db
from api.gcs import get_signed_upload_url
from api.models.alumno import Alumno
from api.models.student_report import StudentReport
from api.schemas.student_report import StudentReportCreate, StudentReportRead, StudentReportUpdate

router = APIRouter(tags=["student_reports"])


def _get_alumno_or_404(alumno_id: int, uid: str, db: Session) -> Alumno:
    a = db.query(Alumno).filter(Alumno.id == alumno_id, Alumno.user_id == uid).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")
    return a


def _get_report_or_404(report_id: int, alumno_id: int, uid: str, db: Session) -> StudentReport:
    r = db.query(StudentReport).filter(
        StudentReport.id == report_id,
        StudentReport.alumno_id == alumno_id,
        StudentReport.user_id == uid,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Informe no encontrado")
    return r


@router.get("/alumnos/{alumno_id}/informes", response_model=list[StudentReportRead])
def listar_informes(
    alumno_id: int,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _get_alumno_or_404(alumno_id, uid, db)
    return (
        db.query(StudentReport)
        .filter(StudentReport.alumno_id == alumno_id, StudentReport.user_id == uid)
        .order_by(StudentReport.created_at.desc())
        .all()
    )


@router.post("/alumnos/{alumno_id}/informes", response_model=StudentReportRead, status_code=201)
def crear_informe(
    alumno_id: int,
    data: StudentReportCreate,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _get_alumno_or_404(alumno_id, uid, db)
    now = datetime.now(UTC)
    report = StudentReport(
        alumno_id=alumno_id,
        user_id=uid,
        diagnostico=data.diagnostico,
        recomendaciones_especialista=data.recomendaciones_especialista,
        created_at=now,
        updated_at=now,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.put("/alumnos/{alumno_id}/informes/{report_id}", response_model=StudentReportRead)
def actualizar_informe(
    alumno_id: int,
    report_id: int,
    data: StudentReportUpdate,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _get_alumno_or_404(alumno_id, uid, db)
    report = _get_report_or_404(report_id, alumno_id, uid, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(report, field, value)
    report.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(report)
    return report


@router.delete("/alumnos/{alumno_id}/informes/{report_id}", status_code=204)
def eliminar_informe(
    alumno_id: int,
    report_id: int,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _get_alumno_or_404(alumno_id, uid, db)
    report = _get_report_or_404(report_id, alumno_id, uid, db)
    db.delete(report)
    db.commit()


@router.post("/alumnos/{alumno_id}/informes/{report_id}/pdf/signed-url")
def generar_signed_url(
    alumno_id: int,
    report_id: int,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _get_alumno_or_404(alumno_id, uid, db)
    _get_report_or_404(report_id, alumno_id, uid, db)

    blob_name = f"informes/{uid}/{alumno_id}/{report_id}.pdf"
    upload_url, final_url = get_signed_upload_url(blob_name)
    return {"upload_url": upload_url, "final_url": final_url}
