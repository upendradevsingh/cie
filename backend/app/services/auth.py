"""JWT validation service for CIE.

CIE does NOT manage users. It validates JWTs issued by calling services
and extracts tenant_id and user_id from the claims.
"""
import logging
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=True)


class TokenClaims(BaseModel):
    tenant_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    sub: Optional[str] = None


def decode_token(token: str) -> TokenClaims:
    """Validate JWT signature and extract claims.

    Accepts both snake_case (tenant_id) and camelCase (tenantId) claim names
    to support different calling services.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as e:
        logger.warning("JWT validation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Accept both snake_case and camelCase claim names
    tenant_id = payload.get("tenant_id") or payload.get("tenantId")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing tenant_id claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_raw = payload.get("user_id") or payload.get("userId")

    try:
        parsed_tenant_id = uuid.UUID(str(tenant_id))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid tenant_id (must be UUID): {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # user_id is optional and may not be a UUID (e.g., service accounts)
    parsed_user_id = None
    if user_id_raw:
        try:
            parsed_user_id = uuid.UUID(str(user_id_raw))
        except ValueError:
            logger.debug("user_id '%s' is not a UUID — treating as service account", user_id_raw)

    return TokenClaims(
        tenant_id=parsed_tenant_id,
        user_id=parsed_user_id,
        sub=payload.get("sub"),
    )


def get_token_claims(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> TokenClaims:
    """FastAPI dependency: validate Bearer token and return claims."""
    return decode_token(credentials.credentials)
