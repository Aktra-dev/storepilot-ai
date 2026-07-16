"""
Authentication & Authorization — Pydantic schemas.

Defines request/response DTOs for register, login, token refresh,
password reset, and user profile.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.modules.auth.models import UserRole

# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    """Register a new user account."""
    name: str = Field(..., min_length=1, max_length=255, description="Full name")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(
        ..., min_length=8, max_length=128, description="Password"
    )
    role: UserRole = Field(default=UserRole.STAFF, description="User role")

class LoginRequest(BaseModel):
    """Authenticate and receive tokens."""
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")

class RefreshTokenRequest(BaseModel):
    """Request a new access token using a refresh token."""
    refresh_token: str = Field(..., description="Refresh token")

class ChangePasswordRequest(BaseModel):
    """Change password for authenticated user."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ..., min_length=8, max_length=128, description="New password"
    )

class ForgotPasswordRequest(BaseModel):
    """Request a password reset email."""
    email: EmailStr = Field(..., description="Email address")

class ResetPasswordRequest(BaseModel):
    """Reset password using a reset token."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(
        ..., min_length=8, max_length=128, description="New password"
    )

class UpdateProfileRequest(BaseModel):
    """Update user profile information."""
    name: Optional[str] = Field(default=None, max_length=255)

class UpdateUserRoleRequest(BaseModel):
    """Admin-only: update another user's role."""
    role: UserRole = Field(..., description="New role")

# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------

class UserResponse(BaseModel):
    """Public user profile (safe for API responses)."""
    id: UUID
    name: str
    email: str
    role: UserRole
    created_at: datetime

    model_config = {"from_attributes": True}

class TokenResponse(BaseModel):
    """JWT token pair."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")

class AuthResponse(BaseModel):
    """Response for login/register with tokens plus user info."""
    user: UserResponse
    tokens: TokenResponse

class MessageResponse(BaseModel):
    """Simple message response."""
    message: str
