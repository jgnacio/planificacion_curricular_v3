import os
from dataclasses import dataclass

import httpx
from fastapi import Header, HTTPException, Query
from jose import JWTError, jwt

CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL", "")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")

_jwks_cache: dict | None = None


def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        if not CLERK_JWKS_URL:
            raise HTTPException(status_code=500, detail="CLERK_JWKS_URL no configurada")
        r = httpx.get(CLERK_JWKS_URL, timeout=10.0)
        r.raise_for_status()
        _jwks_cache = r.json()
    return _jwks_cache


@dataclass
class UserContext:
    user_id: str
    role: str | None
    institution_tenant_id: str | None


def _decode_token(token: str) -> dict:
    jwks = _get_jwks()
    return jwt.decode(
        token,
        jwks,
        algorithms=["RS256"],
        options={"verify_aud": False},
    )


async def get_current_user_id(
    authorization: str | None = Header(None),
    x_internal_key: str | None = Header(None, alias="x-internal-key"),
    user_id: str | None = Query(None),
) -> str:
    if x_internal_key and INTERNAL_API_KEY and x_internal_key == INTERNAL_API_KEY:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id requerido para llamadas internas")
        return user_id

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            payload = _decode_token(token)
            uid: str = payload.get("sub", "")
            if not uid:
                raise HTTPException(status_code=401, detail="JWT no contiene sub claim")
            return uid
        except JWTError as e:
            raise HTTPException(status_code=401, detail=f"JWT inválido: {e}")

    raise HTTPException(status_code=401, detail="Authorization requerida")


async def get_current_user(
    authorization: str | None = Header(None),
    x_internal_key: str | None = Header(None, alias="x-internal-key"),
    user_id: str | None = Query(None),
) -> UserContext:
    if x_internal_key and INTERNAL_API_KEY and x_internal_key == INTERNAL_API_KEY:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id requerido para llamadas internas")
        return UserContext(user_id=user_id, role=None, institution_tenant_id=None)

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            payload = _decode_token(token)
            uid: str = payload.get("sub", "")
            if not uid:
                raise HTTPException(status_code=401, detail="JWT no contiene sub claim")
            meta: dict = payload.get("public_metadata", {})
            return UserContext(
                user_id=uid,
                role=meta.get("role"),
                institution_tenant_id=meta.get("institution_tenant_id"),
            )
        except JWTError as e:
            raise HTTPException(status_code=401, detail=f"JWT inválido: {e}")

    raise HTTPException(status_code=401, detail="Authorization requerida")


def require_institution_admin(user: UserContext) -> UserContext:
    if user.role != "institution_admin" or not user.institution_tenant_id:
        raise HTTPException(status_code=403, detail="Se requiere rol institution_admin")
    return user


async def require_internal_key(
    x_internal_key: str | None = Header(None, alias="x-internal-key"),
) -> None:
    """Valida X-Internal-Key sin scoping por usuario — para recursos globales
    (no por tenant) como la búsqueda de currículo."""
    if not INTERNAL_API_KEY or x_internal_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="X-Internal-Key inválida o ausente")
