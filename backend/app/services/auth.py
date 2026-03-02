"""Authentication and authorization service.

Provides password hashing, JWT token management, and FastAPI dependencies for
extracting the current user and enforcing role-based access control.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Callable, List
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import TokenData

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return ``True`` when *plain* matches the *hashed* password."""
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT containing *data* as claims.

    Parameters
    ----------
    data:
        Arbitrary claims to embed.  Must include at least ``sub``,
        ``tenant_id``, and ``role``.
    expires_delta:
        Optional custom lifetime.  Defaults to
        ``settings.ACCESS_TOKEN_EXPIRE_MINUTES``.

    Returns
    -------
    str
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_token(token: str) -> dict:
    """Decode and validate a JWT.

    Parameters
    ----------
    token:
        The raw JWT string.

    Returns
    -------
    dict
        The decoded payload.

    Raises
    ------
    HTTPException (401)
        If the token is invalid, expired, or missing required claims.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        if payload.get("sub") is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Decode the Bearer token and return the corresponding ``User`` row.

    Raises ``401`` when the token is invalid or the user no longer exists,
    and ``403`` when the user account has been deactivated.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)

    user_id_str: str | None = payload.get("sub")
    tenant_id_str: str | None = payload.get("tenant_id")
    role: str | None = payload.get("role")

    if user_id_str is None or tenant_id_str is None or role is None:
        raise credentials_exception

    try:
        user_id = UUID(user_id_str)
    except (ValueError, TypeError):
        raise credentials_exception

    user: User | None = (
        db.query(User)
        .filter(User.id == user_id, User.tenant_id == UUID(tenant_id_str))
        .first()
    )

    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Return the current user only if their account is active.

    Raises ``403`` when the user's ``is_active`` flag is ``False``.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )
    return current_user


def require_role(roles: List[str]) -> Callable[..., User]:
    """Dependency factory that restricts access to users with one of *roles*.

    Usage in a route::

        @router.get("/admin-only")
        def admin_view(user: User = Depends(require_role(["admin"]))):
            ...

    Parameters
    ----------
    roles:
        Allowed role names, e.g. ``["admin", "team_lead"]``.

    Returns
    -------
    Callable
        A FastAPI dependency that returns the ``User`` if authorized,
        otherwise raises ``403``.
    """

    def _role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        # ``User.role`` is a ``UserRole`` enum — compare against its value.
        user_role = (
            current_user.role.value
            if hasattr(current_user.role, "value")
            else str(current_user.role)
        )
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role(s): {roles}",
            )
        return current_user

    return _role_checker
