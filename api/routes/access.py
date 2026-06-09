from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.access_control import check_agent_access, check_max_plan_access
from api.auth import UserContext, get_current_user
from api.database import get_db

router = APIRouter(prefix="/access", tags=["access"])


class AgentAccessResponse(BaseModel):
    has_access: bool
    kind: str | None = None
    reason: str | None = None
    message: str | None = None


_REASON_MESSAGES = {
    "no_subscription": (
        "Necesitás una suscripción activa para usar el agente. "
        "Suscribite o pedile a tu institución que te asigne una licencia."
    ),
    "institution_unpaid": (
        "Tu institución no tiene un ciclo de facturación pagado y vigente. "
        "Contactá al administrador de tu institución."
    ),
}


@router.get("/plan")
def get_plan_access(
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return {"has_max": check_max_plan_access(user.user_id, db)}


@router.get("/agent", response_model=AgentAccessResponse)
def get_agent_access(
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentAccessResponse:
    has_access, kind, reason = check_agent_access(user.user_id, db)
    return AgentAccessResponse(
        has_access=has_access,
        kind=kind,
        reason=reason,
        message=None if has_access else _REASON_MESSAGES.get(reason or "", _REASON_MESSAGES["no_subscription"]),
    )
