"""Control de acceso al agente IA.

Dos caminos válidos:
1. Suscripción individual `authorized` (IndividualSubscription)
2. Licencia institucional `assigned` con ciclo de facturación pagado y vigente
"""
from datetime import datetime, UTC
from typing import Literal

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth import UserContext, get_current_user
from api.database import get_db
from api.models.billing import (
    IndividualSubscription,
    InstitutionBillingCycle,
    License,
)

AccessKind = Literal["individual", "institutional"]


def check_agent_access(
    user_id: str, db: Session
) -> tuple[bool, AccessKind | None, str | None]:
    """Devuelve (has_access, kind, deny_reason).

    deny_reason existe solo cuando has_access=False y queremos un mensaje específico.
    """
    sub = db.query(IndividualSubscription).filter(
        IndividualSubscription.user_id == user_id,
        IndividualSubscription.status == "authorized",
    ).first()
    if sub:
        return True, "individual", None

    license = db.query(License).filter(
        License.assigned_to == user_id,
        License.status == "assigned",
    ).first()
    if not license:
        return False, None, "no_subscription"

    now = datetime.now(UTC)
    cycle = (
        db.query(InstitutionBillingCycle)
        .filter(
            InstitutionBillingCycle.institution_tenant_id == license.institution_tenant_id,
            InstitutionBillingCycle.status == "paid",
            InstitutionBillingCycle.period_end >= now,
        )
        .order_by(InstitutionBillingCycle.period_end.desc())
        .first()
    )
    if cycle:
        return True, "institutional", None

    return False, None, "institution_unpaid"


_DENY_MESSAGES = {
    "no_subscription": (
        "Necesitás una suscripción activa para usar el agente. "
        "Suscribite o pedile a tu institución que te asigne una licencia."
    ),
    "institution_unpaid": (
        "Tu institución no tiene un ciclo de facturación pagado y vigente. "
        "Contactá al administrador de tu institución."
    ),
}


async def require_agent_access(
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserContext:
    """Dependency FastAPI: bloquea con 402 si no hay acceso al agente."""
    has_access, _kind, reason = check_agent_access(user.user_id, db)
    if not has_access:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "subscription_required",
                "reason": reason or "no_subscription",
                "message": _DENY_MESSAGES.get(reason or "", _DENY_MESSAGES["no_subscription"]),
            },
        )
    return user
