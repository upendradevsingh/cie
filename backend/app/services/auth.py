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
    """Validate JWT signature and extract claims."""
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

    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing tenant_id claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return TokenClaims(
            tenant_id=uuid.UUID(str(tenant_id)),
            user_id=uuid.UUID(str(payload["user_id"])) if payload.get("user_id") else None,
            sub=payload.get("sub"),
        )
    except (ValueError, KeyError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token claims: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_token_claims(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> TokenClaims:
    """FastAPI dependency: validate Bearer token and return claims."""
    return decode_token(credentials.credentials)
