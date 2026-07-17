"""
Authentication dependency for FastAPI routes.

Provides `get_current_user` dependency that extracts and validates
the JWT from the Authorization header. Use this in any protected
endpoint to require authentication.

Example usage in a router:

    from fastapi import Depends
    from app.core.auth import get_current_user
    from app.modules.auth.models import User

    @router.get("/protected")
    def protected_endpoint(current_user: User = Depends(get_current_user)):
        return {"message": f"Hello {current_user.name}"}
"""

from typing import Optional

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import UnauthorizedException
from app.core.security import verify_access_token, AuthenticationError
from app.modules.auth.models import User
from app.modules.auth.service import AuthService


async def get_current_user(
    authorization: str = Header(..., description="Bearer token"),
    db: Session = Depends(get_db),
) -> User:
    """
    Extract and validate current user from JWT in Authorization header.

    This dependency:
    1. Parses the Authorization header (expects "Bearer <token>")
    2. Verifies the JWT signature and expiration
    3. Returns the corresponding User object

    Raises:
        UnauthorizedException: If token is missing, invalid, or user not found.
    """
    # Parse Authorization header
    if not authorization:
        raise UnauthorizedException("Authorization header is missing")

    scheme, token = authorization.split(maxsplit=1) if " " in authorization else ("", "")

    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedException(
            "Invalid authorization format. Use: Authorization: Bearer <token>"
        )

    # Verify token and get user
    auth_service = AuthService(db)
    user = auth_service.get_current_user(token)
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that ensures the user is active.

    Use this instead of get_current_user if you need to check
    user status (active/inactive/deleted).
    """
    # Could add is_active check here in the future
    return current_user


async def get_current_manager(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that ensures the user is a manager.

    Raises ForbiddenException if user is not a MANAGER.
    """
    if current_user.role.value != "manager":
        raise UnauthorizedException("Manager role required")
    return current_user


async def get_current_store_staff_or_manager(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Sales is only in the Manager and Store Staff menus — Inventory Staff
    only manages stock and task monitoring, never sales (per spec).
    """
    from app.modules.auth.models import UserRole

    if current_user.role not in (UserRole.MANAGER, UserRole.STORE_STAFF):
        raise UnauthorizedException(
            "Requires manager or store staff role"
        )
    return current_user


def require_role(required_role: str):
    """
    Create a dependency that requires a specific role.

    Example usage:
        @router.get("/admin-only")
        def admin_endpoint(user: User = Depends(require_role("manager"))):
            return {"message": "Admin only"}

    Args:
        required_role: Required role value ("manager", "store_staff", "inventory_staff")

    Returns:
        FastAPI dependency function
    """
    async def role_dependency(
        current_user: User = Depends(get_current_user),
    ) -> User:
        from app.core.exceptions import ForbiddenException
        from app.modules.auth.models import UserRole

        # Staff roles are equal-level (both below manager); only MANAGER
        # sits above them in the hierarchy.
        role_hierarchy = {
            UserRole.STORE_STAFF: 1,
            UserRole.INVENTORY_STAFF: 1,
            UserRole.MANAGER: 2,
        }

        user_role_level = role_hierarchy.get(current_user.role, 0)
        required_role_enum = UserRole(required_role)
        required_role_level = role_hierarchy.get(required_role_enum, 0)

        if user_role_level < required_role_level:
            raise ForbiddenException(
                f"Insufficient permissions. Requires {required_role} role or higher."
            )

        return current_user

    return role_dependency