"""Integration and API key management routes."""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.integration import ApiKey, Integration
from app.models.user import User
from app.schemas.integration import (
    ApiKeyCreate,
    ApiKeyListResponse,
    ApiKeyResponse,
    IntegrationCreate,
    IntegrationResponse,
    IntegrationUpdate,
)
from app.services.auth import require_role

router = APIRouter(prefix="/integrations", tags=["Integrations"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_api_key() -> tuple[str, str]:
    """Generate a random API key and return ``(plain_key, key_hash)``.

    The key is 48 bytes of URL-safe random data prefixed with ``sl_``
    (SalesLens).  The hash is SHA-256 for fast lookup.
    """
    raw = secrets.token_urlsafe(48)
    plain_key = f"sl_{raw}"
    key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
    return plain_key, key_hash


# =========================================================================
# API Key CRUD  (registered BEFORE /{integration_id} to avoid path conflicts)
# =========================================================================


# ---------------------------------------------------------------------------
# GET /integrations/api-keys
# ---------------------------------------------------------------------------


@router.get(
    "/api-keys",
    response_model=List[ApiKeyListResponse],
    summary="List all API keys for the current tenant",
)
def list_api_keys(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
    include_inactive: bool = Query(default=False, description="Include revoked keys"),
) -> List[ApiKeyListResponse]:
    """Return all API keys for the tenant.

    The raw key value is **never** returned in list views.
    Only admins can view API keys.
    """
    query = db.query(ApiKey).filter(
        ApiKey.tenant_id == current_user.tenant_id,
    )

    if not include_inactive:
        query = query.filter(ApiKey.is_active.is_(True))

    keys = query.order_by(ApiKey.created_at.desc()).all()
    return [ApiKeyListResponse.model_validate(k) for k in keys]


# ---------------------------------------------------------------------------
# POST /integrations/api-keys
# ---------------------------------------------------------------------------


@router.post(
    "/api-keys",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a new API key",
)
def create_api_key(
    body: ApiKeyCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> ApiKeyResponse:
    """Generate a new API key for webhook authentication.

    The plain-text key is returned **only once** in this response.
    Subsequent list/detail calls will not expose the key.
    Only admins can create API keys.
    """
    plain_key, key_hash = _generate_api_key()

    api_key = ApiKey(
        tenant_id=current_user.tenant_id,
        name=body.name,
        key_hash=key_hash,
        is_active=True,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return ApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key=plain_key,
        created_at=api_key.created_at,
    )


# ---------------------------------------------------------------------------
# DELETE /integrations/api-keys/{key_id}
# ---------------------------------------------------------------------------


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an API key",
)
def revoke_api_key(
    key_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> None:
    """Revoke an API key by setting ``is_active=False``.

    The key hash is preserved for audit purposes.
    Only admins can revoke keys.
    """
    api_key = (
        db.query(ApiKey)
        .filter(
            ApiKey.id == key_id,
            ApiKey.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    api_key.is_active = False
    db.commit()


# =========================================================================
# Integration CRUD
# =========================================================================


# ---------------------------------------------------------------------------
# GET /integrations
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=List[IntegrationResponse],
    summary="List all integrations for the current tenant",
)
def list_integrations(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
    include_inactive: bool = Query(default=False, description="Include disabled integrations"),
) -> List[IntegrationResponse]:
    """Return all CRM / webhook integrations configured for the tenant.

    Only admins can view integrations.
    """
    query = db.query(Integration).filter(
        Integration.tenant_id == current_user.tenant_id,
    )

    if not include_inactive:
        query = query.filter(Integration.is_active.is_(True))

    integrations = query.order_by(Integration.created_at.desc()).all()
    return [IntegrationResponse.model_validate(i) for i in integrations]


# ---------------------------------------------------------------------------
# POST /integrations
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=IntegrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new integration",
)
def create_integration(
    body: IntegrationCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> IntegrationResponse:
    """Register a new CRM or webhook integration for the tenant.

    Only admins can create integrations.
    """
    integration = Integration(
        tenant_id=current_user.tenant_id,
        name=body.name,
        type=body.type,
        config=body.config,
        is_active=True,
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)

    return IntegrationResponse.model_validate(integration)


# ---------------------------------------------------------------------------
# GET /integrations/{integration_id}
# ---------------------------------------------------------------------------


@router.get(
    "/{integration_id}",
    response_model=IntegrationResponse,
    summary="Get a specific integration",
)
def get_integration(
    integration_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> IntegrationResponse:
    """Return the details of a specific integration."""
    integration = (
        db.query(Integration)
        .filter(
            Integration.id == integration_id,
            Integration.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if integration is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )

    return IntegrationResponse.model_validate(integration)


# ---------------------------------------------------------------------------
# PUT /integrations/{integration_id}
# ---------------------------------------------------------------------------


@router.put(
    "/{integration_id}",
    response_model=IntegrationResponse,
    summary="Update an integration",
)
def update_integration(
    integration_id: UUID,
    body: IntegrationUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> IntegrationResponse:
    """Update an existing integration. Only admins can modify integrations."""
    integration = (
        db.query(Integration)
        .filter(
            Integration.id == integration_id,
            Integration.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if integration is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(integration, field, value)

    db.commit()
    db.refresh(integration)

    return IntegrationResponse.model_validate(integration)


# ---------------------------------------------------------------------------
# DELETE /integrations/{integration_id}
# ---------------------------------------------------------------------------


@router.delete(
    "/{integration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete an integration",
)
def delete_integration(
    integration_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> None:
    """Disable an integration by setting ``is_active=False``.

    Only admins can delete integrations.
    """
    integration = (
        db.query(Integration)
        .filter(
            Integration.id == integration_id,
            Integration.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if integration is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )

    integration.is_active = False
    db.commit()
