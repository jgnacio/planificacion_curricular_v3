import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth import get_current_user_id
from api.database import get_db
from api.models.chat_session import ChatSession
from api.schemas.chat_session import ChatSessionRead, SessionMessage

router = APIRouter(prefix="/agente/sessions", tags=["agente"])


@router.get("/", response_model=list[ChatSessionRead])
async def list_sessions(
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[ChatSessionRead]:
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == uid)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return sessions


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    row = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == uid)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(row)
    db.commit()


@router.get("/{ap_session_id}/messages", response_model=list[SessionMessage])
async def get_session_messages(
    ap_session_id: str,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[SessionMessage]:
    row = (
        db.query(ChatSession)
        .filter(ChatSession.ap_session_id == ap_session_id, ChatSession.user_id == uid)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    engine_name = os.getenv("AGENT_ENGINE_RESOURCE_NAME", "")
    if not engine_name:
        return []

    try:
        import vertexai
        from vertexai import agent_engines
        vertexai.init(
            project=os.getenv("GOOGLE_CLOUD_PROJECT", ""),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )
        agent = agent_engines.get(engine_name)
        session_data = agent.get_session(user_id=uid, session_id=ap_session_id)
        events = session_data.get("events", []) or []

        messages: list[SessionMessage] = []
        for ev in events:
            author = ev.get("author", "")
            parts = (ev.get("content") or {}).get("parts", []) or []
            texts = [
                p["text"] for p in parts
                if p.get("text") and not p.get("toolCall")
            ]
            if not texts:
                continue
            role = "user" if author == "user" else "agent"
            messages.append(SessionMessage(role=role, text=texts[0]))

        return messages
    except Exception:
        return []
