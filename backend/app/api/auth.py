"""Authentication routes -- login, registration, tenant setup, and profile."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.auth import AuthResponse, AuthTokens, LoginRequest, Token
from app.schemas.tenant import TenantResponse
from app.schemas.user import UserCreate, UserResponse
from app.services.auth import (
    create_access_token,
    get_current_active_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# Request schema for tenant bootstrap (kept here since it combines tenant
# + user creation and is only used by one endpoint).
# ---------------------------------------------------------------------------


class TenantSetupRequest(BaseModel):
    """Combined payload for creating a tenant and its first admin user."""

    tenant_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Organization / company name",
    )
    tenant_slug: str = Field(
        ...,
        min_length=2,
        max_length=63,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="URL-safe slug (lowercase alphanumeric + hyphens)",
    )
    admin_email: EmailStr = Field(
        ...,
        description="Email for the first admin user",
    )
    admin_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password for the admin user",
    )
    admin_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Full name for the admin user",
    )


class TenantSetupResponse(BaseModel):
    """Response returned after successful tenant + admin creation."""

    tenant: TenantResponse
    user: UserResponse
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Authenticate and obtain a JWT token",
)
def login(
    body: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AuthResponse:
    """Validate email and password, then return a signed JWT access token.

    The token embeds the user ID, tenant ID, and role as claims.
    """
    user: User | None = (
        db.query(User)
        .filter(User.email == body.email)
        .first()
    )

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    token_data = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
    }
    access_token = create_access_token(data=token_data)
    refresh_token = create_access_token(data={**token_data, "type": "refresh"})

    return AuthResponse(
        user=UserResponse.model_validate(user),
        tokens=AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        ),
    )


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user within an existing tenant",
)
def register(
    body: UserCreate,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    """Create a new user account.

    The very first user registered for a given tenant is automatically
    promoted to the **admin** role.  Subsequent users receive the role
    specified in the request body (defaults to ``agent``).

    Returns **409** if the email is already taken.
    """
    existing = db.query(User).filter(User.email == body.email).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    # Require at least one tenant to exist.
    tenant = (
        db.query(Tenant)
        .filter(Tenant.is_active.is_(True))
        .order_by(Tenant.created_at.desc())
        .first()
    )
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active tenant found. Create a tenant first via POST /auth/tenant.",
        )

    # First user in the tenant becomes admin automatically.
    tenant_user_count = (
        db.query(User).filter(User.tenant_id == tenant.id).count()
    )
    role = UserRole.admin if tenant_user_count == 0 else UserRole(body.role)

    user = User(
        tenant_id=tenant.id,
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the currently authenticated user",
)
def me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    """Return profile information for the user identified by the Bearer token."""
    return UserResponse.model_validate(current_user)


# ---------------------------------------------------------------------------
# POST /auth/tenant
# ---------------------------------------------------------------------------


@router.post(
    "/tenant",
    response_model=TenantSetupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tenant and its first admin user",
)
def create_tenant(
    body: TenantSetupRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TenantSetupResponse:
    """Bootstrap a brand-new tenant together with the initial admin user.

    This is the very first endpoint to call when setting up SalesLens for a
    new organization.  It creates the ``Tenant`` row and a ``User`` row with
    the **admin** role.

    Returns the tenant details, user profile, and a JWT token so the admin
    can immediately start using the API.
    """
    # Ensure slug is unique
    existing_tenant = (
        db.query(Tenant).filter(Tenant.slug == body.tenant_slug).first()
    )
    if existing_tenant is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A tenant with slug '{body.tenant_slug}' already exists",
        )

    # Ensure email is unique
    existing_user = db.query(User).filter(User.email == body.admin_email).first()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    # Create tenant
    tenant = Tenant(
        name=body.tenant_name,
        slug=body.tenant_slug,
        is_active=True,
    )
    db.add(tenant)
    db.flush()  # Obtain tenant.id without committing

    # Create admin user
    admin_user = User(
        tenant_id=tenant.id,
        email=body.admin_email,
        hashed_password=hash_password(body.admin_password),
        full_name=body.admin_name,
        role=UserRole.admin,
        is_active=True,
    )
    db.add(admin_user)
    db.commit()
    db.refresh(tenant)
    db.refresh(admin_user)

    # Issue token so the admin can start working immediately
    access_token = create_access_token(
        data={
            "sub": str(admin_user.id),
            "tenant_id": str(tenant.id),
            "role": admin_user.role.value,
        }
    )

    return TenantSetupResponse(
        tenant=TenantResponse.model_validate(tenant),
        user=UserResponse.model_validate(admin_user),
        access_token=access_token,
        token_type="bearer",
    )
