"""
Custom application exceptions.

Services/modules should raise these instead of generic Exception, so the
global exception handler can return a consistent, structured error response.
"""


class AppException(Exception):
    """Base exception for all predictable, application-level errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundException(AppException):
    """Raised when a requested resource does not exist."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message=message, status_code=404)


class ValidationException(AppException):
    """Raised when input data fails business-level validation."""

    def __init__(self, message: str = "Invalid input") -> None:
        super().__init__(message=message, status_code=422)


class UnauthorizedException(AppException):
    """Raised when authentication is missing or invalid."""

    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message=message, status_code=401)


class ForbiddenException(AppException):
    """Raised when the authenticated user lacks permission."""

    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message=message, status_code=403)
