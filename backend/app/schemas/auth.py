"""Authentication and authorization schemas."""

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserResponse


class TokenData(BaseModel):
    """Decoded JWT token payload."""

    sub: str = Field(..., description="Subject — the user ID as a string")
    tenant_id: str = Field(..., description="Tenant the user belongs to")
    role: str = Field(..., description="User role (admin, team_lead, agent)")


class Token(BaseModel):
    """Response returned after successful authentication."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type (always bearer)")


class AuthTokens(BaseModel):
    """Token pair returned to the frontend."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type (always bearer)")


class AuthResponse(BaseModel):
    """Full login/register response expected by the frontend."""

    user: UserResponse
    tokens: AuthTokens


class LoginRequest(BaseModel):
    """Credentials submitted to obtain a token."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User password (min 8 characters)",
    )
