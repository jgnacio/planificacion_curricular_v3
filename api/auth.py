import os

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


async def get_current_user_id(
    authorization: str | None = Header(None),
    x_internal_key: str | None = Header(None, alias="x-internal-key"),
    user_id: str | None = Query(None),
) -> str:
    """
    Dependency de FastAPI. Retorna el user_id autenticado.

    Acepta dos formas de auth:
    - JWT de Clerk en Authorization: Bearer <token> → extrae sub claim
    - X-Internal-Key header (para llamadas del Agent Engine) → usa user_id query param
    """
    if x_internal_key and INTERNAL_API_KEY and x_internal_key == INTERNAL_API_KEY:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id requerido para llamadas internas")
        return user_id

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            jwks = _get_jwks()
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )
            uid: str = payload.get("sub", "")
            if not uid:
                raise HTTPException(status_code=401, detail="JWT no contiene sub claim")
            return uid
        except JWTError as e:
            raise HTTPException(status_code=401, detail=f"JWT inválido: {e}")

    raise HTTPException(status_code=401, detail="Authorization requerida")
