import logging
import os
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.access_control import require_max_plan
from api.auth import get_current_user_id, UserContext
from api.database import get_db
from api.models.alumno import Alumno
from api.models.descripcion_fundada import DescripcionFundada
from api.schemas.descripcion_fundada import (
    DescripcionFundadaCreate,
    DescripcionFundadaGenerarPreview,
    DescripcionFundadaRead,
    DescripcionFundadaUpdate,
)

router = APIRouter(tags=["descripciones_fundadas"], dependencies=[Depends(require_max_plan)])


def _gemini_client():
    from google import genai
    api_key = os.getenv("AI_STUDIO_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="API key de Google AI no configurada.")
    return genai.Client(api_key=api_key, vertexai=False)

NIVEL_LABELS = {
    1: "Avance Mínimo (calificación 1-2): el estudiante evidencia dificultades para avanzar en los logros propuestos en la unidad curricular",
    2: "Avance Escaso (calificación 3-4): el desempeño evidencia logros reducidos al abordar contenidos básicos y activar procesos cognitivos simples",
    3: "Avance Moderado (calificación 5-6): el desempeño evidencia logros solamente al abordar contenidos básicos y activar procesos cognitivos simples",
    4: "Avance Significativo (calificación 7-8): activa procesos cognitivos al abordar los contenidos programáticos y logra desempeños parciales de los criterios de logro",
    5: "Avance Destacado (calificación 9-10): activa procesos cognitivos complejos al abordar los contenidos programáticos y logra los desempeños descritos en los criterios de logro",
}

ESPACIO_NOMBRES = {
    "espacio_cientifico_matematico": "Espacio Científico-Matemático",
    "espacio_comunicacion": "Espacio de Comunicación",
    "espacio_ciencias_sociales": "Espacio Ciencias Sociales y Humanidades",
    "espacio_creativo_artistico": "Espacio Creativo-Artístico",
    "espacio_desarrollo_personal": "Espacio de Desarrollo Personal y Conciencia Corporal",
    "espacio_tecnico_tecnologico": "Espacio Técnico-Tecnológico",
}


def _get_alumno_or_404(alumno_id: int, uid: str, db: Session) -> Alumno:
    a = db.query(Alumno).filter(Alumno.id == alumno_id, Alumno.user_id == uid).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")
    return a


def _get_desc_or_404(desc_id: int, alumno_id: int, uid: str, db: Session) -> DescripcionFundada:
    d = db.query(DescripcionFundada).filter(
        DescripcionFundada.id == desc_id,
        DescripcionFundada.alumno_id == alumno_id,
        DescripcionFundada.user_id == uid,
    ).first()
    if not d:
        raise HTTPException(status_code=404, detail="Descripción fundada no encontrada")
    return d


@router.get("/alumnos/{alumno_id}/descripciones-fundadas", response_model=list[DescripcionFundadaRead])
def listar_descripciones(
    alumno_id: int,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _get_alumno_or_404(alumno_id, uid, db)
    return (
        db.query(DescripcionFundada)
        .filter(DescripcionFundada.alumno_id == alumno_id, DescripcionFundada.user_id == uid)
        .order_by(DescripcionFundada.anio.desc(), DescripcionFundada.bimestre.desc())
        .all()
    )


@router.post("/alumnos/{alumno_id}/descripciones-fundadas", response_model=DescripcionFundadaRead, status_code=201)
def crear_descripcion(
    alumno_id: int,
    data: DescripcionFundadaCreate,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _get_alumno_or_404(alumno_id, uid, db)
    now = datetime.now(UTC)
    desc = DescripcionFundada(
        alumno_id=alumno_id,
        user_id=uid,
        bimestre=data.bimestre,
        anio=data.anio,
        espacios_desempeno={k: v.model_dump() for k, v in data.espacios_desempeno.items()},
        desempeno_relacional=data.desempeno_relacional,
        sugerencias=data.sugerencias,
        created_at=now,
        updated_at=now,
    )
    db.add(desc)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe una descripción fundada para el bimestre {data.bimestre} del año {data.anio}",
        )
    db.refresh(desc)
    return desc


@router.get("/alumnos/{alumno_id}/descripciones-fundadas/{desc_id}", response_model=DescripcionFundadaRead)
def obtener_descripcion(
    alumno_id: int,
    desc_id: int,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _get_alumno_or_404(alumno_id, uid, db)
    return _get_desc_or_404(desc_id, alumno_id, uid, db)


@router.put("/alumnos/{alumno_id}/descripciones-fundadas/{desc_id}", response_model=DescripcionFundadaRead)
def actualizar_descripcion(
    alumno_id: int,
    desc_id: int,
    data: DescripcionFundadaUpdate,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _get_alumno_or_404(alumno_id, uid, db)
    desc = _get_desc_or_404(desc_id, alumno_id, uid, db)
    update_data = data.model_dump(exclude_unset=True)
    if "espacios_desempeno" in update_data and update_data["espacios_desempeno"] is not None:
        update_data["espacios_desempeno"] = {
            k: v.model_dump() if hasattr(v, "model_dump") else v
            for k, v in update_data["espacios_desempeno"].items()
        }
    for field, value in update_data.items():
        setattr(desc, field, value)
    desc.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(desc)
    return desc


@router.delete("/alumnos/{alumno_id}/descripciones-fundadas/{desc_id}", status_code=204)
def eliminar_descripcion(
    alumno_id: int,
    desc_id: int,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _get_alumno_or_404(alumno_id, uid, db)
    desc = _get_desc_or_404(desc_id, alumno_id, uid, db)
    db.delete(desc)
    db.commit()


@router.post("/alumnos/{alumno_id}/descripciones-fundadas/generar-preview")
def generar_descripcion_preview(
    alumno_id: int,
    data: DescripcionFundadaGenerarPreview,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _get_alumno_or_404(alumno_id, uid, db)

    espacios_texto = ""
    for espacio_key, espacio in data.espacios_desempeno.items():
        nombre = ESPACIO_NOMBRES.get(espacio_key, espacio_key)
        descriptor = NIVEL_LABELS.get(espacio.nivel_avance, "")
        if espacio.observacion.strip():
            espacios_texto += f"\n- **{nombre}**: {descriptor}. Observación del docente: {espacio.observacion}"
        else:
            espacios_texto += f"\n- **{nombre}**: {descriptor}."

    bimestre_label = f"{data.bimestre}° bimestre {data.anio}"

    prompt = f"""Eres un asistente pedagógico experto en el sistema educativo uruguayo (ANEP/EBI).
Tu tarea es redactar la Descripción Fundada de un estudiante según el artículo 14 del REDE (ANEP 2022) y la Circular 7/2020.

**Datos del estudiante:**
- Nombre: {data.alumno_nombre}
- Nivel: {data.alumno_nivel}
- Grado/Tramo: {data.alumno_grado}
- Período: {bimestre_label}

**Desempeño por Espacio del conocimiento:**
{espacios_texto}

**Desempeño relacional (con pares y docentes):**
{data.desempeno_relacional}

**Sugerencias para mejorar:**
{data.sugerencias}

**Instrucciones obligatorias para la redacción (Circular 7/2020):**
1. Usa EXCLUSIVAMENTE tiempo verbal presente (lo que el estudiante está logrando ahora)
2. Usa lenguaje positivo: "Muestra avances en…", "Demuestra…", "Logra…", "Evidencia…", "Trabaja…"
3. NUNCA uses palabras negativas ni juicios de valor
4. El texto debe ser claro, concreto y comprensible para la familia
5. Contextualiza al estudiante de manera singular (no comparativa)
6. Si requiere apoyos o acompañamientos específicos, mencionarlo explícitamente
7. El tono debe ser estimulante y empático

**Estructura obligatoria del texto:**
1. Párrafo inicial: aspectos positivos y fortalezas del estudiante
2. Párrafo central: desempeño por cada Espacio del conocimiento (mencionando el nivel de avance de forma descriptiva, no numérica)
3. Párrafo de mejora: áreas donde puede seguir creciendo, con consejos concretos orientados a la familia
4. Párrafo final: mensaje motivacional que aliente al estudiante a continuar

Redacta la descripción fundada completa en español, en un solo bloque de texto organizado en 4 párrafos.
"""

    try:
        from google.genai import types as genai_types

        client = _gemini_client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=1024,
            ),
        )
        return {"descripcion_generada": response.text.strip()}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error en generar descripción: %s", e)
        raise HTTPException(status_code=500, detail=f"Error al generar la descripción: {str(e)}")


@router.post("/alumnos/{alumno_id}/descripciones-fundadas/{desc_id}/generar", response_model=DescripcionFundadaRead)
def generar_descripcion(
    alumno_id: int,
    desc_id: int,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    alumno = _get_alumno_or_404(alumno_id, uid, db)
    desc = _get_desc_or_404(desc_id, alumno_id, uid, db)

    espacios_texto = ""
    for espacio_key, datos in desc.espacios_desempeno.items():
        nombre = ESPACIO_NOMBRES.get(espacio_key, espacio_key)
        nivel = datos.get("nivel_avance", 3)
        observacion = datos.get("observacion", "")
        descriptor = NIVEL_LABELS.get(nivel, "")
        espacios_texto += f"\n- **{nombre}**: {descriptor}. Observación del docente: {observacion}"

    nombre_alumno = alumno.nombre_completo
    nivel_alumno = alumno.nivel or ""
    grado_alumno = alumno.grado or ""
    bimestre_label = f"{desc.bimestre}° bimestre {desc.anio}"

    prompt = f"""Eres un asistente pedagógico experto en el sistema educativo uruguayo (ANEP/EBI).
Tu tarea es redactar la Descripción Fundada de un estudiante según el artículo 14 del REDE (ANEP 2022) y la Circular 7/2020.

**Datos del estudiante:**
- Nombre: {nombre_alumno}
- Nivel: {nivel_alumno}
- Grado/Tramo: {grado_alumno}
- Período: {bimestre_label}

**Desempeño por Espacio del conocimiento:**
{espacios_texto}

**Desempeño relacional (con pares y docentes):**
{desc.desempeno_relacional}

**Sugerencias para mejorar:**
{desc.sugerencias}

**Instrucciones obligatorias para la redacción (Circular 7/2020):**
1. Usa EXCLUSIVAMENTE tiempo verbal presente (lo que el estudiante está logrando ahora)
2. Usa lenguaje positivo: "Muestra avances en…", "Demuestra…", "Logra…", "Evidencia…", "Trabaja…"
3. NUNCA uses palabras negativas ni juicios de valor
4. El texto debe ser claro, concreto y comprensible para la familia
5. Contextualiza al estudiante de manera singular (no comparativa)
6. Si requiere apoyos o acompañamientos específicos, mencionarlo explícitamente
7. El tono debe ser estimulante y empático

**Estructura obligatoria del texto:**
1. Párrafo inicial: aspectos positivos y fortalezas del estudiante
2. Párrafo central: desempeño por cada Espacio del conocimiento (mencionando el nivel de avance de forma descriptiva, no numérica)
3. Párrafo de mejora: áreas donde puede seguir creciendo, con consejos concretos orientados a la familia
4. Párrafo final: mensaje motivacional que aliente al estudiante a continuar

Redacta la descripción fundada completa en español, en un solo bloque de texto organizado en 4 párrafos.
"""

    try:
        from google.genai import types as genai_types

        client = _gemini_client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=1024,
            ),
        )
        texto_generado = response.text.strip()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error en generar descripción: %s", e)
        raise HTTPException(status_code=500, detail=f"Error al generar la descripción: {str(e)}")

    desc.descripcion_generada = texto_generado
    desc.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(desc)
    return desc
