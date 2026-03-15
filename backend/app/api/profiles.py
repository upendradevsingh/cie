"""Profile listing and retrieval endpoints."""
import logging

from fastapi import APIRouter, HTTPException, status, Depends

from app.profiles import get_profile_loader
from app.schemas.profile import ProfileResponse
from app.services.auth import TokenClaims, get_token_claims

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("", response_model=list[ProfileResponse])
async def list_profiles(
    claims: TokenClaims = Depends(get_token_claims),
) -> list[ProfileResponse]:
    """List all available extraction profiles."""
    loader = get_profile_loader()
    profiles = loader.get_all()
    return [ProfileResponse.model_validate(p.model_dump()) for p in profiles]


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: str,
    claims: TokenClaims = Depends(get_token_claims),
) -> ProfileResponse:
    """Get a specific profile by ID."""
    loader = get_profile_loader()
    try:
        profile = loader.load(profile_id)
    except ValueError:
        available = loader.list_profiles()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{profile_id}' not found. Available: {available}",
        )
    return ProfileResponse.model_validate(profile.model_dump())
