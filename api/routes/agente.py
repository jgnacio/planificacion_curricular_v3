import asyncio
import os
import json
import logging
import traceback

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.auth import get_current_user_id

logger = logging.getLogger(__name__)

AGENT_ENGINE_RESOURCE_NAME = ""
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

# ==========================================
# Modo dev: Runner local con InMemorySessionService
# Modo prod: Agent Engine via vertexai SDK
# Switch: AGENT_ENGINE_RESOURCE_NAME env var
# ==========================================

if not AGENT_ENGINE_RESOURCE_NAME:
    # Dev mode — runner local
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai.types import Content, Part
    from teacher_agent.agent import root_agent

    _session_service = InMemorySessionService()
    _runner = Runner(
        agent=root_agent,
        app_name="facilitador_docente",
        session_service=_session_service,
    )
else:
    # Prod mode — Agent Engine (lazy init para no bloquear el startup)
    import vertexai
    from vertexai import agent_engines

    vertexai.init(project=GOOGLE_CLOUD_PROJECT, location=GOOGLE_CLOUD_LOCATION)
    _remote_agent = None  # se inicializa en el primer request


def _get_remote_agent():
    global _remote_agent
    if _remote_agent is None:
        _remote_agent = agent_engines.get(AGENT_ENGINE_RESOURCE_NAME)
    return _remote_agent


# ==========================================
# REQUEST / RESPONSE SCHEMAS
# ==========================================

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    response: str


router = APIRouter(prefix="/agente", tags=["agente"])

# ==========================================
# TOOL LABELS (para SSE streaming)
# ==========================================

_TOOL_LABELS: dict[str, str] = {
    # Bibliotecario
    "consultar_curriculo_estructurado": "Consultando currículo EBI…",
    "consultar_curriculo_oficial":      "Leyendo programa oficial…",
    # Alumnos
    "listar_alumnos":                   "Consultando lista de alumnos…",
    "crear_alumno":                     "Registrando alumno…",
    "actualizar_alumno":                "Actualizando alumno…",
    "eliminar_alumno":                  "Eliminando alumno…",
    # Planificaciones
    "listar_planificaciones":           "Buscando planificaciones…",
    "crear_planificacion":              "Guardando planificación…",
    "actualizar_planificacion":         "Actualizando planificación…",
    "eliminar_planificacion":           "Eliminando planificación…",
    # Creativo
    "buscar_en_internet":               "Buscando ideas pedagógicas…",
    # Sub-agentes (delegaciones del orquestador)
    "agente_alumnos":                   "Consultando gestión de alumnos…",
    "agente_planificaciones":           "Gestionando planificaciones…",
    "agente_planificador_normativo":    "Consultando currículo oficial…",
    "agente_inclusion":                 "Analizando grupo y adaptaciones…",
    "agente_creativo":                  "Buscando ideas creativas…",
}

# ==========================================
# ENDPOINTS
# ==========================================

@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, uid: str = Depends(get_current_user_id)) -> ChatResponse:
    """
    Envía un mensaje al agente Facilitador Docente EBI.

    En prod (AGENT_ENGINE_RESOURCE_NAME set): llama a Vertex AI Agent Engine.
    En dev (sin AGENT_ENGINE_RESOURCE_NAME): usa runner local.

    El user_id se extrae del JWT Clerk (o X-Internal-Key) y se inyecta en
    el session state para que las tools del agente filtren datos por usuario.
    """
    try:
        if AGENT_ENGINE_RESOURCE_NAME:
            return await _chat_agent_engine(body, uid)
        return await _chat_local(body, uid)
    except Exception as e:
        logger.error("Error en /agente/chat: %s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error interno del agente: {str(e)}") from e


@router.post("/chat/stream")
async def chat_stream(body: ChatRequest, uid: str = Depends(get_current_user_id)) -> StreamingResponse:
    """
    SSE endpoint — emite eventos de tool calls + respuesta final.
    Formato: data: {"type": "tool"|"done"|"error", ...}
    """
    async def generate():
        try:
            async for evt in _stream_local(body, uid):
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error("Error en /agente/chat/stream: %s\n%s", e, traceback.format_exc())
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_local(body: ChatRequest, user_id: str):
    """Generador async — yield eventos SSE del runner local."""
    from google.genai.types import Content, Part

    sid = body.session_id
    if not sid:
        session = await _session_service.create_session(
            app_name="facilitador_docente",
            user_id=user_id,
            state={"user_id": user_id},
        )
        sid = session.id
    else:
        session = await _session_service.get_session(
            app_name="facilitador_docente",
            user_id=user_id,
            session_id=sid,
        )
        if not session:
            session = await _session_service.create_session(
                app_name="facilitador_docente",
                user_id=user_id,
                session_id=sid,
                state={"user_id": user_id},
            )
            sid = session.id

    response_text = ""
    async for event in _runner.run_async(
        user_id=user_id,
        session_id=sid,
        new_message=Content(parts=[Part(text=body.message)]),
    ):
        # Detectar tool calls y delegaciones a sub-agentes — emitir label amigable
        if event.content and event.content.parts:
            for part in event.content.parts:
                fn = getattr(part, "function_call", None)
                if fn and fn.name:
                    label = _TOOL_LABELS.get(fn.name, f"{fn.name}…")
                    yield {"type": "tool", "tool": fn.name, "label": label}

        if event.is_final_response():
            if event.content and event.content.parts:
                response_text = getattr(event.content.parts[0], "text", "") or ""
            break

    # Stream token a token el campo `text` del JSON de respuesta
    # Esto da el efecto visual de ChatGPT mientras la respuesta estructurada llega completa al final
    try:
        parsed = json.loads(response_text)
        text_to_stream = parsed.get("text", "")
        if text_to_stream:
            words = text_to_stream.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield {"type": "token", "text": chunk}
                await asyncio.sleep(0.022)  # ~45 palabras/seg
    except Exception:
        pass  # Si no es JSON válido, el done lo maneja

    yield {"type": "done", "session_id": sid, "response": response_text}


async def _chat_local(body: ChatRequest, user_id: str) -> ChatResponse:
    """Runner local para desarrollo."""
    from google.genai.types import Content, Part

    sid = body.session_id

    if not sid:
        session = await _session_service.create_session(
            app_name="facilitador_docente",
            user_id=user_id,
            state={"user_id": user_id},
        )
        sid = session.id
    else:
        session = await _session_service.get_session(
            app_name="facilitador_docente",
            user_id=user_id,
            session_id=sid,
        )
        if not session:
            session = await _session_service.create_session(
                app_name="facilitador_docente",
                user_id=user_id,
                session_id=sid,
                state={"user_id": user_id},
            )
            sid = session.id

    response_text = ""
    async for event in _runner.run_async(
        user_id=user_id,
        session_id=sid,
        new_message=Content(parts=[Part(text=body.message)]),
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                response_text = event.content.parts[0].text
            break

    return ChatResponse(session_id=sid, response=response_text)


async def _chat_agent_engine(body: ChatRequest, user_id: str) -> ChatResponse:
    """Proxy a Vertex AI Agent Engine via stream_query (ADK)."""
    import asyncio

    agent = _get_remote_agent()
    loop = asyncio.get_event_loop()

    # Crear o reusar sesión
    def _get_or_create_session(sid: str | None) -> str:
        if sid:
            try:
                session = agent.get_session(user_id=user_id, session_id=sid)
                return session["id"]
            except Exception:
                pass
        session = agent.create_session(user_id=user_id)
        return session["id"]

    sid = await loop.run_in_executor(None, _get_or_create_session, body.session_id)

    # Enviar mensaje y colectar respuesta final
    def _stream():
        response_text = ""
        for event in agent.stream_query(
            user_id=user_id,
            session_id=sid,
            message=body.message,
        ):
            # El evento final tiene el texto de respuesta
            if isinstance(event, dict):
                content = event.get("content", {})
                if isinstance(content, dict):
                    parts = content.get("parts", [])
                    for part in parts:
                        if isinstance(part, dict) and part.get("text"):
                            response_text = part["text"]
            # También puede ser un string directo
            elif isinstance(event, str):
                response_text = event
        return response_text

    response_text = await loop.run_in_executor(None, _stream)
    return ChatResponse(session_id=sid, response=response_text or "El agente no respondió.")
