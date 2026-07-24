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

# Límite duro del sistema (Circular 7/2020): nunca puede superarse.
LONGITUD_MIN = 1500
LONGITUD_MAX = 2000
LONGITUD_OBJETIVO = 1650  # centro del rango "óptimo" 1500-1800 — da margen antes de tocar el límite duro
_MAX_INTENTOS_GENERACION = 3


def _truncar_a_limite(texto: str, max_chars: int = LONGITUD_MAX) -> str:
    """Garantía dura: corta en el último punto de oración antes del límite,
    nunca a media palabra. Última línea de defensa si los reintentos a la IA fallan."""
    if len(texto) <= max_chars:
        return texto
    cortado = texto[:max_chars]
    ultimo_punto = max(cortado.rfind(". "), cortado.rfind(".\n"))
    if ultimo_punto > max_chars * 0.6:
        return cortado[: ultimo_punto + 1].strip()
    ultimo_espacio = cortado.rfind(" ")
    if ultimo_espacio > max_chars * 0.6:
        return cortado[:ultimo_espacio].rstrip() + "."
    return cortado.rstrip()


def _generar_texto_ia(prompt_base: str) -> str:
    """Llama a Gemini y garantiza que el resultado quede en [LONGITUD_MIN, LONGITUD_MAX].

    Los LLM no cuentan caracteres con precisión, así que no alcanza con pedirlo en el
    prompt (lo confirmamos en producción: pedimos 1500-2000 y devolvió 2413). Por eso:
    1. Reintenta hasta _MAX_INTENTOS_GENERACION veces, informando el largo real obtenido.
    2. Si ningún intento cae en rango, trunca de forma determinística — el límite de
       LONGITUD_MAX NUNCA se excede, pase lo que pase con el modelo.
    """
    from google.genai import types as genai_types

    client = _gemini_client()
    prompt_actual = prompt_base
    ultimo_texto = ""

    for _ in range(_MAX_INTENTOS_GENERACION):
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt_actual,
            config=genai_types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=4096,
                thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
            ),
        )
        texto = response.text.strip()
        ultimo_texto = texto
        largo = len(texto)

        if LONGITUD_MIN <= largo <= LONGITUD_MAX:
            return texto

        if largo > LONGITUD_MAX:
            ajuste = (
                f"\n\nIMPORTANTE: tu respuesta anterior tuvo {largo} caracteres, demasiado larga. "
                f"Reescribí TODO el texto de nuevo, más conciso, apuntando a {LONGITUD_OBJETIVO} "
                f"caracteres. Nunca superes los {LONGITUD_MAX} caracteres."
            )
        else:
            ajuste = (
                f"\n\nIMPORTANTE: tu respuesta anterior tuvo {largo} caracteres, demasiado corta. "
                f"Reescribí TODO el texto de nuevo, más desarrollado, apuntando a {LONGITUD_OBJETIVO} "
                f"caracteres, sin superar los {LONGITUD_MAX}."
            )
        prompt_actual = prompt_base + ajuste

    return _truncar_a_limite(ultimo_texto)


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


def _calcular_edad(fecha_nacimiento: str | None) -> int | None:
    """Calcula la edad en años desde la fecha de nacimiento del alumno.

    El campo es un string libre — intentamos formatos comunes (ISO y dd/mm/yyyy).
    Si está vacío o no se puede parsear, devuelve None (no se menciona la edad)."""
    if not fecha_nacimiento or not fecha_nacimiento.strip():
        return None
    valor = fecha_nacimiento.strip()
    fecha = None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            fecha = datetime.strptime(valor[:10], fmt)
            break
        except ValueError:
            continue
    if fecha is None:
        return None
    hoy = datetime.now()
    edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
    if edad < 0 or edad > 25:  # fuera de rango plausible para Inicial-6° → datos sospechosos, no mencionar
        return None
    return edad


def _construir_prompt_descripcion(
    nombre: str,
    nivel: str,
    grado: str,
    bimestre_label: str,
    espacios_texto: str,
    desempeno_relacional: str,
    sugerencias: str,
    edad: int | None = None,
) -> str:
    if edad is not None:
        edad_info = (
            f"\n**Edad del alumno:** {edad} años (calculada de su fecha de nacimiento). "
            f"Usá esta edad para calibrar bien el registro y la madurez del texto."
        )
    else:
        edad_info = (
            "\n**Edad del alumno:** no disponible. NO menciones la edad del niño ni la inventes; "
            "guiate solo por el grado para calibrar el registro."
        )
    return f"""Sos una maestra uruguaya con muchos años de aula, escribiendo la Descripción Fundada
de uno de tus alumnos para entregarle a su familia. Conocés a este niño, lo viste crecer este período,
y le escribís a la familia con la voz cálida y concreta de alguien que de verdad lo acompañó.
La descripción cumple el artículo 14 del REDE (ANEP 2022) y la Circular 7/2020, pero la escribís
como una persona, no como un formulario.

**Datos del estudiante:**
- Nombre: {nombre}
- Nivel: {nivel}
- Grado/Tramo: {grado}
- Período: {bimestre_label}
{edad_info}

**CLAVE — el grado de este alumno es "{grado}" (nivel "{nivel}"). Ajustá el registro a ese grado:**
El sistema EBI de ANEP (Educación Inicial a 6° de primaria — todos son niños, ninguno es adolescente)
tiene estos grados reales, agrupados en tramos. Ubicá al alumno y escribí acorde:
- Tramo 1 — Educación Inicial: "Nivel 3 años", "Nivel 4 años", "Nivel 5 años".
  Es el jardín. Mundo del juego, la exploración y los primeros descubrimientos. Tono tierno y cercano:
  jugar, compartir, animarse, descubrir.
- Tramo 2 — Primer ciclo de Primaria: "1.er grado", "2.do grado".
  Primeros aprendizajes formales, la lectura y los números que empiezan. Tono cálido y afectivo, celebrando cada conquista.
- Tramo 3 — Segundo ciclo de Primaria: "3.er grado", "4.to grado".
  Más autonomía y esfuerzo sostenido. Tono cálido pero ya no de jardín.
- Tramo 4 — Tercer ciclo de Primaria: "5.to grado", "6.to grado".
  Niños de 10 a 12 años: responsabilidad con sus tareas y vínculos más elaborados. Reconocé su crecimiento
  y tratalo según su edad. NO uses lenguaje de nene chico ("buscar mi mano", "su risita") con ellos: sonaría
  fuera de lugar. Sigue siendo un niño, pero más grande y más capaz.
Referite al grado SIEMPRE con su nombre real ("{grado}"), nunca lo cambies ni inventes otra forma
(no digas "5to" si es "Nivel 5 años", ni al revés). Si el grado viniera vacío o raro, guiate por las
observaciones del docente y no menciones el grado explícitamente.

**Cómo viene en cada espacio:**
{espacios_texto}

**Cómo se relaciona:**
{desempeno_relacional}

**Lo que la familia puede acompañar:**
{sugerencias}

**REGLA DE ORO — no inventes NADA:**
Escribí ÚNICAMENTE sobre lo que el docente puso en las observaciones de arriba. NO inventes anécdotas,
gestos, momentos, situaciones, actitudes ni rasgos del niño que no estén explícitamente escritos.
Nada de "su risa de cada tarde", "busca mi mano", "su carita de alegría", "siempre saluda al entrar" ni
detalles parecidos si el docente no los mencionó. El tono cálido va en CÓMO escribís, no en agregar hechos
que no te dieron. Si el docente escribió poco, redactá un texto más breve y honesto — preferible corto y
verdadero que largo e inventado. Cada cosa que afirmes tiene que poder rastrearse a las observaciones.

**Reglas que no podés saltarte (REDE / Circular 7/2020):**
- Escribí siempre en presente: lo que el niño LOGRA, demuestra, trabaja o muestra avances en, ahora.
- Todo desde lo positivo y desde las posibilidades. Nunca algo negativo, ni juicios de valor, ni comparaciones con otros niños.
- No menciones números, calificaciones ni "niveles de avance" — traducí eso a palabras concretas sobre lo que el niño hace.
- Si necesita apoyos específicos, decilo con naturalidad, como un consejo de maestra, no como un diagnóstico.
- Lenguaje claro y simple, que cualquier familia entienda.
- NO menciones el liceo, la secundaria, la educación media ni "lo que viene después de la escuela", aunque
  el niño esté en 6° grado. Quedate siempre en el presente escolar de la primaria. Solo podés mencionarlo si
  la docente lo escribió explícitamente en sus observaciones o sugerencias.

**Lo más importante — que NO suene a inteligencia artificial:**
- PROHIBIDO usar muletillas de IA como: "demuestra ser un estudiante", "cabe destacar", "asimismo",
  "es importante mencionar", "valiosas herramientas", "todo su potencial", "enriquece la convivencia",
  "facilita su integración", "actitud sumamente positiva", "gran disposición".
- PROHIBIDO el cierre genérico tipo "¡A seguir adelante con el mismo entusiasmo!" o "¡Felicitaciones!".
  Cerrá retomando con calidez algo CONCRETO que el docente sí escribió (un avance, una fortaleza real
  mencionada en las observaciones). Nunca inventes un detalle para el cierre.
- No expliques de más ni agregues relleno del tipo "lo que le permite...", "favoreciendo así...".
  Si una frase no aporta algo concreto sobre el niño, no la pongas.
- Variá el arranque de las oraciones. No empieces todo con el nombre del niño ni con "En el Espacio de...".
- VARIÁ la frase de apertura del texto. La misma maestra escribe muchas descripciones, así que no pueden
  empezar todas igual. Evitá caer siempre en "Qué alegría me da sentarme a escribirles...". Buscá una entrada
  distinta y genuina cada vez: a veces arrancá por una fortaleza del niño, por cómo lo ves en el aula, por el
  momento del año, por una cualidad suya. Mantené la calidez, pero que el comienzo no sea siempre el mismo molde.
- Escribí como hablás: oraciones de largo natural, alguna más corta, alguna más larga. Que se sienta una persona.

**Forma:** 3 o 4 párrafos que fluyan naturalmente (no uno por cada cosa de la lista). Un solo bloque de texto,
sin títulos ni encabezados ni viñetas. Empezá directamente con la descripción.

**Longitud:** apuntá a {LONGITUD_OBJETIVO} caracteres con espacios. Nunca superes los {LONGITUD_MAX} ni bajes de {LONGITUD_MIN}.
"""


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
    alumno = _get_alumno_or_404(alumno_id, uid, db)

    espacios_texto = ""
    for espacio_key, espacio in data.espacios_desempeno.items():
        nombre = ESPACIO_NOMBRES.get(espacio_key, espacio_key)
        descriptor = NIVEL_LABELS.get(espacio.nivel_avance, "")
        if espacio.observacion.strip():
            espacios_texto += f"\n- **{nombre}**: {descriptor}. Observación del docente: {espacio.observacion}"
        else:
            espacios_texto += f"\n- **{nombre}**: {descriptor}."

    bimestre_label = f"{data.bimestre}° bimestre {data.anio}"

    prompt = _construir_prompt_descripcion(
        nombre=data.alumno_nombre,
        nivel=data.alumno_nivel,
        grado=data.alumno_grado,
        bimestre_label=bimestre_label,
        espacios_texto=espacios_texto,
        desempeno_relacional=data.desempeno_relacional,
        sugerencias=data.sugerencias,
        edad=_calcular_edad(alumno.fecha_nacimiento),
    )

    try:
        texto_generado = _generar_texto_ia(prompt)
        return {"descripcion_generada": texto_generado}
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

    prompt = _construir_prompt_descripcion(
        nombre=nombre_alumno,
        nivel=nivel_alumno,
        grado=grado_alumno,
        bimestre_label=bimestre_label,
        espacios_texto=espacios_texto,
        desempeno_relacional=desc.desempeno_relacional,
        sugerencias=desc.sugerencias,
        edad=_calcular_edad(alumno.fecha_nacimiento),
    )

    try:
        texto_generado = _generar_texto_ia(prompt)
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
