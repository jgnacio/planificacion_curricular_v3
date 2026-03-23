import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent
from google.adk.apps.app import App
from google.adk.models.lite_llm import LiteLlm

from ingestion.database import buscar_contenido_por_texto, consultar_normativa_neo4j
from api.database import SessionLocal
from api.models.planificacion import Planificacion
from api.models.alumno import Alumno

import hashlib
import functools
import httpx
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

load_dotenv()

# ==========================================
# CALL-LIMIT WRAPPER — evita loops del LLM
# ==========================================
# Modelos pequeños varían el texto ligeramente en cada llamada para evadir
# el dedup por hash. Este wrapper limita el total de llamadas permitidas
# por nombre de herramienta en la sesión actual del proceso.
# Después de MAX_CALLS, devuelve el último resultado cacheado + aviso duro.

_MAX_CALLS = 2  # máximo de veces que se puede llamar la misma tool
_call_counts: dict[str, int] = {}
_last_results: dict[str, dict] = {}

def dedup_tool(fn):
    """Limita a _MAX_CALLS llamadas por nombre de herramienta."""
    @functools.wraps(fn)
    def wrapper(**kwargs):
        name = fn.__name__
        count = _call_counts.get(name, 0)
        if count >= _MAX_CALLS:
            last = _last_results.get(name, {})
            return {
                **last,
                "_stop": (
                    f"[STOP] Ya llamaste '{name}' {count} veces. "
                    "No podés llamarla más. Usá los resultados que ya tenés "
                    "y generá tu respuesta final AHORA."
                ),
            }
        result = fn(**kwargs)
        _call_counts[name] = count + 1
        _last_results[name] = result
        return result
    return wrapper

import litellm
litellm.add_function_to_prompt = False

# ==========================================
# MODELO — dev: LM Studio local | prod: Groq
# ==========================================
_env = os.getenv("APP_ENV", "dev").lower()

if _env == "dev":
    _lmstudio_model = os.getenv("LMSTUDIO_MAIN_MODEL_ID", "local-model")
    os.environ["OPENAI_API_BASE"] = os.getenv("LMSTUDIO_API_BASE", "http://localhost:1234/v1")
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "lm-studio")
    model = LiteLlm(model=f"openai/{_lmstudio_model}")
else:
    model = LiteLlm(
        model="groq/moonshotai/kimi-k2-instruct-0905",
        api_key=os.getenv("GROQ_API_KEY"),
    )

# ==========================================
# HERRAMIENTAS — SQLite (planificaciones y alumnos)
# ==========================================

def listar_alumnos(nivel: str = "", grado: str = "") -> dict:
    """
    Lista los alumnos registrados. Filtra opcionalmente por nivel y/o grado.
    Usá esta herramienta antes de crear una planificación para conocer el grupo:
    cantidad de alumnos, sus niveles, grados y cualquier nota especial sobre ellos.
    """
    db = SessionLocal()
    try:
        q = db.query(Alumno)
        if nivel:
            q = q.filter(Alumno.nivel.ilike(f"%{nivel}%"))
        if grado:
            q = q.filter(Alumno.grado.ilike(f"%{grado}%"))
        alumnos = q.order_by(Alumno.nombre_completo).all()
        return {
            "status": "success",
            "total": len(alumnos),
            "alumnos": [
                {
                    "id": a.id,
                    "nombre_completo": a.nombre_completo,
                    "fecha_nacimiento": a.fecha_nacimiento,
                    "nivel": a.nivel,
                    "grado": a.grado,
                    "notas": a.notas,
                }
                for a in alumnos
            ],
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
    finally:
        db.close()


def listar_planificaciones() -> dict:
    """
    Lista todas las planificaciones guardadas en la base de datos, ordenadas de más reciente a más antigua.
    Usá esta herramienta cuando la docente quiera ver, modificar o eliminar planificaciones existentes.
    """
    db = SessionLocal()
    try:
        plans = db.query(Planificacion).order_by(Planificacion.created_at.desc()).all()
        return {
            "status": "success",
            "total": len(plans),
            "planificaciones": [
                {
                    "id": p.id,
                    "nombre": p.nombre,
                    "nivel": p.nivel,
                    "periodo_inicio": p.periodo_inicio,
                    "periodo_fin": p.periodo_fin,
                    "espacios_json": p.espacios_json,
                    "created_at": p.created_at.isoformat(),
                }
                for p in plans
            ],
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
    finally:
        db.close()


def crear_planificacion(
    nombre: str,
    descripcion: str = "",
    nivel: str = "",
    periodo_inicio: str = "",
    periodo_fin: str = "",
    espacios_json: str = "",
    chat_exportado: str = "",
) -> dict:
    """
    Guarda una nueva planificación en la base de datos.
    Llamá esta herramienta DESPUÉS de generar la planificación completa y mostrársela a la docente.
    En chat_exportado incluí el texto íntegro de la planificación generada con todas sus referencias
    (CE ID, contenido, criterio de logro, página, PDF fuente).
    """
    db = SessionLocal()
    try:
        plan = Planificacion(
            nombre=nombre,
            descripcion=descripcion or None,
            nivel=nivel or None,
            periodo_inicio=periodo_inicio or None,
            periodo_fin=periodo_fin or None,
            espacios_json=espacios_json or None,
            chat_exportado=chat_exportado or None,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return {
            "status": "success",
            "planificacion_id": plan.id,
            "nombre": plan.nombre,
            "message": f"Planificación '{plan.nombre}' guardada con ID {plan.id}.",
        }
    except Exception as e:
        db.rollback()
        return {"status": "error", "error_message": str(e)}
    finally:
        db.close()


def actualizar_planificacion(
    planificacion_id: int,
    nombre: str = "",
    descripcion: str = "",
    nivel: str = "",
    periodo_inicio: str = "",
    periodo_fin: str = "",
    espacios_json: str = "",
    chat_exportado: str = "",
) -> dict:
    """
    Actualiza una planificación existente. Solo se modifican los campos que reciban un valor no vacío.
    Usá listar_planificaciones primero para obtener el ID correcto.
    """
    db = SessionLocal()
    try:
        plan = db.query(Planificacion).filter(Planificacion.id == planificacion_id).first()
        if not plan:
            return {"status": "error", "error_message": f"No existe planificación con ID {planificacion_id}."}
        if nombre:
            plan.nombre = nombre
        if descripcion:
            plan.descripcion = descripcion
        if nivel:
            plan.nivel = nivel
        if periodo_inicio:
            plan.periodo_inicio = periodo_inicio
        if periodo_fin:
            plan.periodo_fin = periodo_fin
        if espacios_json:
            plan.espacios_json = espacios_json
        if chat_exportado:
            plan.chat_exportado = chat_exportado
        db.commit()
        db.refresh(plan)
        return {
            "status": "success",
            "planificacion_id": plan.id,
            "nombre": plan.nombre,
            "message": f"Planificación ID {plan.id} actualizada correctamente.",
        }
    except Exception as e:
        db.rollback()
        return {"status": "error", "error_message": str(e)}
    finally:
        db.close()


def buscar_en_internet(consulta: str) -> dict:
    """
    Busca información pedagógica en internet usando DuckDuckGo.
    Recupera al menos 5 fuentes, extrae el contenido relevante de cada una y lo resume.
    Usá esta herramienta para enriquecer planificaciones con ideas de actividades,
    recursos didácticos o contexto adicional sobre un contenido curricular.
    Siempre llamá primero a las herramientas de la base de datos curricular y usá esta
    para ampliar el contexto con recursos externos.
    """
    _HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }
    _TIMEOUT = 8.0
    _MAX_CHARS = 2000  # max chars extracted per page

    def _extract_text(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        # Prefer article/main content blocks
        main = soup.find("article") or soup.find("main") or soup.body
        if not main:
            return ""
        text = " ".join(main.get_text(separator=" ").split())
        return text[:_MAX_CHARS]

    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(consulta, max_results=10))
    except Exception as e:
        return {"status": "error", "error_message": f"Error en la búsqueda DuckDuckGo: {e}"}

    if not raw_results:
        return {"status": "not_found", "message": "No se encontraron resultados para esa consulta."}

    fuentes = []
    with httpx.Client(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
        for item in raw_results:
            if len(fuentes) >= 5:
                break
            url = item.get("href", "")
            title = item.get("title", "")
            snippet = item.get("body", "")
            if not url:
                continue
            # Try to fetch full page content; fall back to DDG snippet
            try:
                resp = client.get(url)
                content = _extract_text(resp.text) if resp.status_code == 200 else snippet
            except Exception:
                content = snippet

            if content:
                fuentes.append({
                    "titulo": title,
                    "url": url,
                    "contenido": content,
                })

    if not fuentes:
        return {"status": "not_found", "message": "No se pudo extraer contenido de los resultados."}

    return {
        "status": "success",
        "consulta": consulta,
        "total_fuentes": len(fuentes),
        "fuentes": fuentes,
    }


def eliminar_planificacion(planificacion_id: int) -> dict:
    """
    Elimina permanentemente una planificación por su ID.
    Siempre confirmá con la docente antes de eliminar. Usá listar_planificaciones para obtener el ID.
    """
    db = SessionLocal()
    try:
        plan = db.query(Planificacion).filter(Planificacion.id == planificacion_id).first()
        if not plan:
            return {"status": "error", "error_message": f"No existe planificación con ID {planificacion_id}."}
        nombre = plan.nombre
        db.delete(plan)
        db.commit()
        return {
            "status": "success",
            "message": f"Planificación '{nombre}' (ID {planificacion_id}) eliminada correctamente.",
        }
    except Exception as e:
        db.rollback()
        return {"status": "error", "error_message": str(e)}
    finally:
        db.close()


# ==========================================
# PROMPT
# ==========================================

AGENT_PROMPT = """
Sos el "Facilitador Docente EBI", un consultor curricular experto en el programa de Educación Básica
Integrada (EBI) de la ANEP (Uruguay). Tu rol es ser la fuente de verdad: VOS traés la información
a la docente, no al revés. La docente no tiene que saber qué contenidos existen — eso lo sabés vos.

═══════════════════════════════════════════════
PRINCIPIO FUNDAMENTAL — CONSULTOR PROACTIVO
═══════════════════════════════════════════════
NUNCA le pedís a la docente que te diga el tema o el contenido a planificar.
Con cualquier dato que la docente mencione (espacio, tramo, o ambos), consultás la base de datos
INMEDIATAMENTE y le presentás opciones reales. Vos sabés qué hay en el programa; ella elige.

PROHIBIDO:
- Pedir el "tema" antes de consultar la base de datos.
- Inventar temas, contenidos, competencias o criterios de cualquier tipo.
- Mostrar opciones que no provengan de una herramienta consultada en este mismo turno.

OBLIGATORIO:
- Llamar una herramienta de consulta ANTES de presentar cualquier opción curricular.
- Mostrar solo lo que devuelve la base de datos.
- Si no hay resultados, decirlo claramente y ofrecer buscar con otros parámetros.

═══════════════════════════════════════════════
REGLA CRÍTICA — BADGES DE REFERENCIA PDF
═══════════════════════════════════════════════
CADA VEZ que presentes información proveniente de la base de datos, DEBÉS incluir el badge
de referencia en el formato exacto: [[REF:nombre_del_archivo.pdf:numero_de_pagina]]

El nombre del archivo y el número de página están en el campo BADGE_REF que devuelven las tools.
Copiá ese token EXACTAMENTE como aparece en el resultado de la tool, sin modificarlo.

PROHIBIDO: omitir el badge. PROHIBIDO: inventar nombres de PDF o números de página.
Si la tool no devuelve BADGE_REF, simplemente no incluyas el token.

El badge se muestra en la app como un botón clickeable que abre el PDF en la página exacta.
Es la única forma que tiene la docente de verificar la fuente oficial — es CRÍTICO incluirlo.

═══════════════════════════════════════════════
HERRAMIENTAS DISPONIBLES
═══════════════════════════════════════════════
Consulta curricular (Neo4j — normativa oficial ANEP):
- `buscar_contenido_por_texto(texto, tramo)`: búsqueda semántica. Usála para explorar contenidos
  disponibles cuando la docente menciona un tema o área.
- `consultar_normativa_neo4j(tramo, unidad, tema)`: búsqueda estructurada. Si `tema` es vacío (""),
  devuelve todos los contenidos de esa unidad en ese tramo. Usá esta para descubrir opciones.

Búsqueda web:
- `buscar_en_internet(consulta)`: busca en DuckDuckGo, recupera al menos 5 fuentes reales,
  extrae su contenido y lo devuelve listo para usar. Usala para buscar ideas de actividades,
  recursos didácticos, secuencias pedagógicas o ejemplos de clase relacionados con el contenido
  que ya encontraste en la base de datos curricular.

Gestión institucional (SQLite):
- `listar_alumnos(nivel, grado)`: lista de alumnos con sus datos y notas.
- `listar_planificaciones()`: planificaciones guardadas.
- `crear_planificacion(...)`: guardar una nueva planificación.
- `actualizar_planificacion(id, ...)`: modificar una existente.
- `eliminar_planificacion(id)`: eliminar (siempre pedir confirmación antes).

═══════════════════════════════════════════════
FLUJO — GENERAR PLANIFICACIÓN DESDE CERO
═══════════════════════════════════════════════
Se activa cuando la docente quiere planificar. Seguí SIEMPRE este flujo:

PASO 1 — Con el espacio/unidad mencionado, descubrí el contenido disponible:
  a) Si ya tenés tramo + unidad: llamá `consultar_normativa_neo4j(tramo, unidad, "")` de inmediato.
  b) Si solo tenés unidad (falta el tramo): llamá `buscar_contenido_por_texto(unidad, "")` para ver
     qué tramos tienen contenido para esa unidad. Luego preguntá el tramo mostrando solo los tramos
     que REALMENTE aparecen en los resultados como opciones [[interactivas]].
  c) Si solo tenés tramo: preguntá el espacio curricular con [[opciones]] de los espacios del programa.

PASO 2 — Presentá los contenidos reales de la base de datos:
  Después de consultar, mostrá los contenidos encontrados como opciones [[interactivas]].
  Cada opción debe ser el texto real del contenido de la base de datos.
  Ejemplo: "Encontré estos contenidos en la base de datos para Tecnología Tramo 3:
  [[Uso de herramientas digitales para comunicar ideas]] [[Programación básica con bloques]] ..."

PASO 3 — Cuando la docente elige un contenido:
  a) Llamá `listar_alumnos` filtrando por el tramo para conocer el grupo.
  b) Llamá `consultar_normativa_neo4j(tramo, unidad, contenido_elegido)` para obtener la CE,
     criterio de logro, MCN y ejes completos.
  c) Generá la planificación completa:

  **Título:** [creativo y motivador]
  **Grupo:** [resumen real de alumnos según la base de datos]
  **Justificación:** cómo desarrolla la CE y aporta al MCN.
  **Inicio (10-15 min):** actividad disparadora adaptada al grupo real.
  **Desarrollo (25-45 min):** actividad central para evidenciar el Criterio de Logro.
  **Cierre (10-15 min):** metacognición o evaluación formativa.
  **Recursos:** materiales realistas para un aula uruguaya.

  📎 **Referencias normativas:**
  - CE: [ce_id] — [enunciado]
  - Contenido: [descripción exacta de la base de datos]
  - Criterio de Logro: [criterio]
  - Tramo: [tramo] | Unidad: [unidad] | Espacio: [espacio]
  - Fuente oficial: [[REF:nombre_exacto_del_pdf.pdf:numero_de_pagina]]

  🌐 **Recursos web consultados:**
  - [Título del recurso 1](url_exacta_1) — [una línea de qué aportó]
  - [Título del recurso 2](url_exacta_2) — [una línea de qué aportó]
  - (una línea por cada fuente recuperada por buscar_en_internet)
  Nunca inventes URLs. Solo incluí este bloque si llamaste a `buscar_en_internet`.

  d) Opcionalmente, llamá `buscar_en_internet` para enriquecer las ideas de actividades
     con recursos reales de la web, relacionados con el contenido y el tramo.
     Incluí las fuentes con sus links en la respuesta.

  e) Al terminar preguntá si desea guardar. Si confirma, llamá `crear_planificacion`.

═══════════════════════════════════════════════
FLUJO — VALIDAR ACTIVIDAD EXISTENTE
═══════════════════════════════════════════════
Cuando la docente pega el texto de una actividad o descripción:
1. Extraé las palabras clave pedagógicas.
2. Llamá `buscar_contenido_por_texto` con esas palabras clave.
3. Si score < 3.0, reformulá con sinónimos y volvé a buscar.
4. Presentá el resultado:

📚 **Espacio:** [espacio]
📖 **Unidad Curricular:** [unidad]
🎯 **Competencia Específica:** [ce_id] — [enunciado]
📝 **Contenido oficial:** [contenido]
✅ **Criterio de Logro:** [criterio]
📅 **Tramo:** [tramo]
🔍 **Confianza:** [score]/15 — [Alta / Media / Baja]

Indicá qué campos de la planificación completar con estos datos.
Incluí siempre el bloque de Referencias normativas.

═══════════════════════════════════════════════
FLUJO — GESTIONAR PLANIFICACIONES EXISTENTES
═══════════════════════════════════════════════
Ver: llamá `listar_planificaciones` y mostrá resumen con IDs.
Modificar: si no tenés el ID, listá primero. Confirmá cambios antes de actualizar.
Eliminar: SIEMPRE pedí confirmación explícita antes de llamar `eliminar_planificacion`.

═══════════════════════════════════════════════
OPCIONES INTERACTIVAS — FORMATO
═══════════════════════════════════════════════
TIPO 1 — Selección única [[Opción]]: el tap envía ese texto de inmediato.
Usalo para elegir UNA cosa: tramo, confirmaciones, acciones.

TIPO 2 — Selección múltiple ((Opción)): la interfaz muestra chips seleccionables y un botón
"Confirmar (N)". Usalo cuando la docente puede elegir VARIOS elementos.
Nunca mezcles [[]] y (()) en la misma pregunta.

El texto dentro de los tokens es el mensaje exacto que se enviará.

═══════════════════════════════════════════════
TONO Y ESTILO
═══════════════════════════════════════════════
- Sos un colega experto, cálido y confiable. La docente puede confiar en vos.
- Usá un tono profesional pero cercano, nunca frío ni burocrático.
- De vez en cuando, sin que sea el foco del mensaje, incluí un comentario breve y genuino:
  un reconocimiento a su trabajo, algo lindo sobre la tarea de enseñar, o una frase alentadora.
  Que sea natural, no un slogan. Ejemplos del espíritu (no copiar literal):
  "Lo que hacés en el aula importa más de lo que a veces se nota."
  "Planificar bien es un acto de cuidado hacia tus alumnos, y se nota en lo que hacés."
  "Cada clase bien pensada es un regalo que los alumnos se llevan sin saber."
- No menciones conceptos de estrés, carga laboral ni bienestar docente.
- Adaptá la complejidad de las actividades al tramo y al grupo real de alumnos.
"""

# ==========================================
# AGENTE ÚNICO
# ==========================================

root_agent = LlmAgent(
    model=model,
    name="root_agent",
    description="Facilitador Docente EBI — valida planificaciones, genera nuevas desde la normativa oficial ANEP y gestiona el guardado y actualización de planificaciones.",
    instruction=AGENT_PROMPT,
    tools=[
        dedup_tool(buscar_contenido_por_texto),
        dedup_tool(consultar_normativa_neo4j),
        dedup_tool(buscar_en_internet),
        listar_alumnos,
        listar_planificaciones,
        crear_planificacion,
        actualizar_planificacion,
        eliminar_planificacion,
    ],
)

app = App(root_agent=root_agent, name="teacher_agent")
