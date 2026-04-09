import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import get_current_user_id

AGENT_ENGINE_RESOURCE_NAME = os.getenv("AGENT_ENGINE_RESOURCE_NAME", "")
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
# ENDPOINT
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
        raise HTTPException(status_code=500, detail=f"Error interno del agente: {str(e)}") from e


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
    """Proxy a Vertex AI Agent Engine."""
    sid = body.session_id or f"session-{user_id}"

    import asyncio
    loop = asyncio.get_event_loop()

    def _query():
        return _get_remote_agent().query(
            input=body.message,
            config={"configurable": {"session_id": sid, "user_id": user_id}},
        )

    result = await loop.run_in_executor(None, _query)

    # Extraer texto de la respuesta
    if isinstance(result, dict):
        response_text = result.get("output", result.get("response", str(result)))
    else:
        response_text = str(result)

    return ChatResponse(session_id=sid, response=response_text)
