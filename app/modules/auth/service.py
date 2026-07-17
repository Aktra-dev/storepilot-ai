"""
Authentication & Authorization — business logic.

Handles:
- User registration (with password hashing)
- Login with JWT token issuance (access + refresh)
- Token refresh
- Password management (change, reset)
- User profile CRUD
- Role-based access control
- User listing/admin
"""

import uuid
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.exceptions import (
    AppException,
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    ValidationException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_access_token,
    verify_refresh_token,
    blacklist_token,
    hash_password,
    verify_password,
    validate_password_strength,
    generate_password_reset_token,
    verify_password_reset_token,
    is_rate_limited,
    record_failed_login,
    clear_failed_logins,
    AuthenticationError,
    PasswordValidationError,
)
from app.modules.auth.models import User, UserRole


class AuthService:
    """
    Authentication and authorization service.

    Every method is a unit of business logic — no HTTP-level concerns
    (headers, cookies, request objects) leak in here.
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Register
    # ------------------------------------------------------------------

    def register(self, name: str, email: str, password: str, role=None) -> dict:
        """
        Register a new user account.

        SECURITY: role is always forced to STORE_STAFF here (least-privilege
        default). Any `role` passed in (e.g. from the request body) is
        ignored — self-registering as MANAGER would be a
        privilege-escalation bug. Roles can only be changed afterwards via
        PATCH /auth/users/{id}/role (manager only).

        Returns user data + tokens on success.
        Raises ValidationException if email already exists or password is weak.
        """
        # Check email uniqueness
        existing = self.db.query(User).filter(User.email == email).first()
        if existing:
            raise ValidationException("Email already registered")

        # Validate password strength
        password_errors = validate_password_strength(password)
        if password_errors:
            raise ValidationException(" / ".join(password_errors))

        # Hash password and create user
        hashed = hash_password(password)
        user = User(
            id=uuid.uuid4(),
            name=name,
            email=email,
            password_hash=hashed,
            role=UserRole.STORE_STAFF,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # Generate tokens
        tokens = self._generate_tokens(user)
        return {"user": user, "tokens": tokens}

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    def login(self, email: str, password: str) -> dict:
        """
        Authenticate user with email and password.

        Returns user data + tokens on success.
        Raises UnauthorizedException on invalid credentials.
        """
        if is_rate_limited(email):
            raise UnauthorizedException(
                "Terlalu banyak percobaan login gagal. Coba lagi dalam beberapa menit."
            )

        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            record_failed_login(email)
            raise UnauthorizedException("Invalid email or password")

        if not verify_password(password, user.password_hash):
            record_failed_login(email)
            raise UnauthorizedException("Invalid email or password")

        clear_failed_logins(email)
        tokens = self._generate_tokens(user)
        return {"user": user, "tokens": tokens}

    # ------------------------------------------------------------------
    # Token Management
    # ------------------------------------------------------------------

    def refresh_token(self, refresh_token: str) -> dict:
        """
        Issue a new access token using a valid refresh token.

        Raises UnauthorizedException if refresh token is invalid/expired.
        """
        try:
            payload = verify_refresh_token(refresh_token)
        except AuthenticationError as e:
            raise UnauthorizedException(str(e))

        user_id = payload.get("user_id")
        if not user_id:
            raise UnauthorizedException("Invalid refresh token payload")

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UnauthorizedException("User not found")

        access_token = create_access_token(
            data={
                "user_id": str(user.id),
                "email": user.email,
                "role": user.role.value,
            }
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,  # Return same refresh token
            "token_type": "bearer",
        }

    def logout(self, access_token: str) -> None:
        """
        Logout user by blacklisting their current access token.
        """
        blacklist_token(access_token)

    # ------------------------------------------------------------------
    # Get Current User
    # ------------------------------------------------------------------

    def get_current_user(self, token: str) -> User:
        """
        Decode JWT token and return the corresponding User object.

        Raises UnauthorizedException if token is invalid or user is deleted.
        """
        try:
            payload = verify_access_token(token)
        except AuthenticationError as e:
            raise UnauthorizedException(str(e))

        user_id = payload.get("user_id")

        if payload.get("type") != "access":
            raise UnauthorizedException("Invalid token type")

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UnauthorizedException("User not found")

        return user

    def get_current_active_user(self, token: str) -> User:
        """
        Same as get_current_user but ensures the user has a valid role.
        """
        user = self.get_current_user(token)

        # Could add is_active check here in the future
        return user

    # ------------------------------------------------------------------
    # Profile Management
    # ------------------------------------------------------------------

    def get_profile(self, user_id: uuid.UUID) -> User:
        """
        Get user profile by ID.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")
        return user

    def update_profile(self, user_id: uuid.UUID, name: Optional[str]) -> User:
        """
        Update user profile information.
        """
        user = self.get_profile(user_id)

        if name is not None:
            user.name = name

        self.db.commit()
        self.db.refresh(user)
        return user

    # ------------------------------------------------------------------
    # Password Management
    # ------------------------------------------------------------------

    def change_password(
        self, user_id: uuid.UUID, current_password: str, new_password: str
    ) -> None:
        """
        Change password for authenticated user.

        Requires current password verification.
        """
        user = self.get_profile(user_id)

        if not verify_password(current_password, user.password_hash):
            raise UnauthorizedException("Current password is incorrect")

        password_errors = validate_password_strength(new_password)
        if password_errors:
            raise ValidationException(" / ".join(password_errors))

        user.password_hash = hash_password(new_password)
        self.db.commit()

    def forgot_password(self, email: str) -> dict:
        """
        Initiate password reset flow.

        In production, this would send an email with the reset token.
        For now, returns the token directly for development/testing.
        """
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            # Don't reveal whether the email exists (security best practice)
            return {
                "message": "If the email is registered, you will receive password reset instructions.",
            }

        reset_token = generate_password_reset_token(str(user.id))

        # TODO: In production, send email with reset_token
        # For development, return token in response
        return {
            "message": "If the email is registered, you will receive password reset instructions.",
            "reset_token": reset_token,  # Only for development
        }

    def reset_password(self, token: str, new_password: str) -> None:
        """
        Reset password using a valid reset token.
        """
        try:
            user_id = verify_password_reset_token(token)
        except AuthenticationError as e:
            raise UnauthorizedException(str(e))

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UnauthorizedException("Invalid reset token")

        password_errors = validate_password_strength(new_password)
        if password_errors:
            raise ValidationException(" / ".join(password_errors))

        user.password_hash = hash_password(new_password)
        self.db.commit()

    # ------------------------------------------------------------------
    # Admin: User Management
    # ------------------------------------------------------------------

    def list_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """
        List all users (admin only).
        """
        return (
            self.db.query(User)
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_user_by_id(self, user_id: uuid.UUID) -> User:
        """
        Get any user by ID (admin only).
        """
        return self.get_profile(user_id)

    def update_user_role(self, user_id: uuid.UUID, new_role: UserRole) -> User:
        """
        Update another user's role (admin only).
        """
        user = self.get_profile(user_id)
        user.role = new_role
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_user(self, user_id: uuid.UUID) -> None:
        """
        Delete a user account (admin only).

        TODO: Consider soft-delete instead of hard-delete for auditing.
        """
        user = self.get_profile(user_id)
        self.db.delete(user)
        self.db.commit()

    # ------------------------------------------------------------------
    # Authorization Helpers
    # ------------------------------------------------------------------

    def require_role(self, user: User, required_role: UserRole) -> None:
        """
        Check if user has the required role.

        Raises ForbiddenException if insufficient permissions.
        """
        role_hierarchy = {
            UserRole.STORE_STAFF: 1,
            UserRole.INVENTORY_STAFF: 1,
            UserRole.MANAGER: 2,
        }

        if role_hierarchy.get(user.role, 0) < role_hierarchy.get(required_role, 0):
            raise ForbiddenException(
                f"Requires {required_role.value} role or higher"
            )

    def require_manager(self, user: User) -> None:
        """Check if user is a manager."""
        if user.role != UserRole.MANAGER:
            raise ForbiddenException("Manager role required")

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _generate_tokens(self, user: User) -> dict:
        """Generate access + refresh token pair for a user."""
        token_data = {
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role.value,
        }

        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data=token_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
