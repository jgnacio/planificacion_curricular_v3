from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from neo4j.exceptions import ServiceUnavailable

from teacher_agent.agent import root_agent


# ==========================================
# REQUEST / RESPONSE SCHEMAS
# ==========================================

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    user_id: str = "maestra"


class ChatResponse(BaseModel):
    session_id: str
    response: str


# ==========================================
# SINGLETONS — inicializados al cargar el módulo
# ==========================================

_session_service = InMemorySessionService()
_runner = Runner(
    agent=root_agent,
    app_name="facilitador_docente",
    session_service=_session_service,
)

router = APIRouter(prefix="/agente", tags=["agente"])


# ==========================================
# ENDPOINT
# ==========================================

@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest) -> ChatResponse:
    """
    Envía un mensaje al agente Facilitador Docente EBI y retorna su respuesta.

    - Si `session_id` es None o no existe, se crea una sesión nueva.
    - La sesión persiste en memoria mientras la app esté corriendo.
    - Retorna el `session_id` para que el cliente lo reutilice en el siguiente turno.
    """
    try:
        sid = body.session_id

        if not sid:
            # Primer mensaje — crear sesión nueva (async en ADK >= 1.x)
            session = await _session_service.create_session(
                app_name="facilitador_docente",
                user_id=body.user_id,
            )
            sid = session.id
        else:
            # Turno siguiente — recuperar sesión existente o crearla con el ID dado
            session = await _session_service.get_session(
                app_name="facilitador_docente",
                user_id=body.user_id,
                session_id=sid,
            )
            if not session:
                session = await _session_service.create_session(
                    app_name="facilitador_docente",
                    user_id=body.user_id,
                    session_id=sid,
                )
                sid = session.id

        response_text = ""
        async for event in _runner.run_async(
            user_id=body.user_id,
            session_id=sid,
            new_message=Content(parts=[Part(text=body.message)]),
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    response_text = event.content.parts[0].text
                break

        return ChatResponse(session_id=sid, response=response_text)

    except ServiceUnavailable as e:
        raise HTTPException(
            status_code=503,
            detail="Graph database unavailable. Verificá que Neo4j esté corriendo."
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del agente: {str(e)}"
        ) from e
