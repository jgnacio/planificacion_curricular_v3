"""
Dependencias compartidas entre rutas.
"""
from sqlalchemy.orm import Session

from api.models.user_profile import UserProfile


def ensure_user_profile(uid: str, db: Session) -> None:
    """Crea un UserProfile mínimo si no existe.

    Necesario porque groups, activities y sequences tienen FK a users_profile.
    El perfil real se actualiza cuando el usuario completa sus datos en la app.
    """
    exists = (
        db.query(UserProfile.clerk_user_id)
        .filter(UserProfile.clerk_user_id == uid)
        .first()
    )
    if not exists:
        db.add(UserProfile(clerk_user_id=uid, email=f"{uid}@auto.local"))
        db.commit()
