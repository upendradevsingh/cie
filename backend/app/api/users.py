"""User management routes -- CRUD for tenant users."""

from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.auth import get_current_active_user, hash_password, require_role

router = APIRouter(prefix="/users", tags=["Users"])


# ---------------------------------------------------------------------------
# GET /users
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=List[UserResponse],
    summary="List users in the current tenant",
)
def list_users(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["admin", "team_lead"]))],
    include_inactive: bool = Query(
        default=False,
        description="Include deactivated users",
    ),
    role: str | None = Query(
        default=None,
        description="Filter by role: admin, team_lead, or agent",
    ),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=100, description="Results per page"),
) -> List[UserResponse]:
    """Return a paginated list of users belonging to the current tenant.

    Only admins and team leads can view the user list.
    """
    query = db.query(User).filter(
        User.tenant_id == current_user.tenant_id,
    )

    if not include_inactive:
        query = query.filter(User.is_active.is_(True))

    if role:
        role_val = role.lower()
        if role_val in {r.value for r in UserRole}:
            query = query.filter(User.role == UserRole(role_val))

    users = (
        query.order_by(User.full_name)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return [UserResponse.model_validate(u) for u in users]


# ---------------------------------------------------------------------------
# POST /users
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user in the current tenant",
)
def create_user(
    body: UserCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> UserResponse:
    """Create a new user account within the current tenant.

    Only admins can create users.  Returns **409** if the email already
    exists within the tenant.
    """
    # Check for duplicate email within the tenant
    existing = (
        db.query(User)
        .filter(
            User.tenant_id == current_user.tenant_id,
            User.email == body.email,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists in this tenant",
        )

    user = User(
        tenant_id=current_user.tenant_id,
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=UserRole(body.role),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


# ---------------------------------------------------------------------------
# PUT /users/{user_id}
# ---------------------------------------------------------------------------


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a user",
)
def update_user(
    user_id: UUID,
    body: UserUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> UserResponse:
    """Update an existing user's profile, role, or active status.

    Only admins can update users.  Admins cannot deactivate their own
    account through this endpoint.
    """
    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent self-deactivation
    if user.id == current_user.id and body.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    update_data = body.model_dump(exclude_unset=True)

    # Convert role string to enum if present
    if "role" in update_data and update_data["role"] is not None:
        update_data["role"] = UserRole(update_data["role"])

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


# ---------------------------------------------------------------------------
# DELETE /users/{user_id}
# ---------------------------------------------------------------------------


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a user",
)
def deactivate_user(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> None:
    """Soft-delete (deactivate) a user by setting ``is_active=False``.

    The user's data is preserved but they can no longer authenticate.
    Only admins can deactivate users.  Self-deactivation is not allowed.
    """
    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    user.is_active = False
    db.commit()
