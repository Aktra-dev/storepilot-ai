"""
Authentication & Authorization — API routes.

Public endpoints (no auth):
    POST /auth/register
    POST /auth/login
    POST /auth/refresh
    POST /auth/forgot-password
    POST /auth/reset-password

Protected endpoints (JWT required):
    GET    /auth/me
    PATCH  /auth/me
    POST   /auth/me/change-password
    POST   /auth/logout

Admin endpoints (manager only):
    GET    /auth/users
    GET    /auth/users/{id}
    PATCH  /auth/users/{id}/role
    DELETE /auth/users/{id}
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_active_user, get_current_manager
from app.core.database import get_db
from app.modules.auth.models import User, UserRole
from app.modules.auth.schemas import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
    UpdateUserRoleRequest,
    UserResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter()


# =========================================================================
# Helper: get service instance
# =========================================================================

def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db=db)


# =========================================================================
# PUBLIC ENDPOINTS (No Auth)
# =========================================================================

@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(
    payload: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
):
    """Create a new user account. Returns user profile + JWT tokens."""
    return service.register(
        name=payload.name,
        email=payload.email,
        password=payload.password,
        role=payload.role,
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login with email & password",
)
def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
):
    """Authenticate and return user profile + JWT tokens."""
    return service.login(email=payload.email, password=payload.password)


@router.post(
    "/refresh",
    response_model=dict,
    summary="Refresh access token",
)
def refresh_token(
    payload: RefreshTokenRequest,
    service: AuthService = Depends(get_auth_service),
):
    """Get a new access token using a refresh token."""
    return service.refresh_token(payload.refresh_token)


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset",
)
def forgot_password(
    payload: ForgotPasswordRequest,
    service: AuthService = Depends(get_auth_service),
):
    """Send password reset instructions (returns token in dev mode)."""
    return service.forgot_password(payload.email)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password with token",
)
def reset_password(
    payload: ResetPasswordRequest,
    service: AuthService = Depends(get_auth_service),
):
    """Reset password using a valid reset token."""
    service.reset_password(token=payload.token, new_password=payload.new_password)
    return {"message": "Password reset successful"}


# =========================================================================
# PROTECTED ENDPOINTS (JWT Required)
# =========================================================================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
def get_me(
    current_user: User = Depends(get_current_active_user),
):
    """Return the authenticated user's profile."""
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
def update_me(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_active_user),
    service: AuthService = Depends(get_auth_service),
):
    """Update name or other profile fields for the authenticated user."""
    return service.update_profile(
        user_id=current_user.id,
        name=payload.name,
    )


@router.post(
    "/me/change-password",
    response_model=MessageResponse,
    summary="Change current user password",
)
def change_my_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    service: AuthService = Depends(get_auth_service),
):
    """Change password. Requires current password verification."""
    service.change_password(
        user_id=current_user.id,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return {"message": "Password changed successfully"}


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout (blacklist token)",
)
def logout(
    authorization: str = Header(..., description="Bearer token"),
    service: AuthService = Depends(get_auth_service),
):
    """
    Logout the current user by blacklisting their access token.

    The token is extracted from the Authorization header.
    """
    # Extract token from header
    token = authorization.replace("Bearer ", "").strip() if authorization.startswith("Bearer ") else ""
    service.logout(token)
    return {"message": "Logged out successfully"}


# =========================================================================
# ADMIN ENDPOINTS (Manager Only)
# =========================================================================

@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List all users (admin)",
)
def list_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: User = Depends(get_current_manager),
    service: AuthService = Depends(get_auth_service),
):
    """Return paginated list of all users. Requires manager role."""
    return service.list_users(skip=skip, limit=limit)


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID (admin)",
)
def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_manager),
    service: AuthService = Depends(get_auth_service),
):
    """Return any user by ID. Requires manager role."""
    return service.get_user_by_id(user_id)


@router.patch(
    "/users/{user_id}/role",
    response_model=UserResponse,
    summary="Update user role (admin)",
)
def update_user_role(
    user_id: UUID,
    payload: UpdateUserRoleRequest,
    current_user: User = Depends(get_current_manager),
    service: AuthService = Depends(get_auth_service),
):
    """Change a user's role. Requires manager role."""
    return service.update_user_role(user_id, payload.role)


@router.delete(
    "/users/{user_id}",
    response_model=MessageResponse,
    summary="Delete user (admin)",
)
def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_manager),
    service: AuthService = Depends(get_auth_service),
):
    """Permanently delete a user account. Requires manager role."""
    service.delete_user(user_id)
    return {"message": f"User {user_id} deleted"}