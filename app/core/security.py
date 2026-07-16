"""
Security utilities for authentication and authorization.

Includes:
- Password hashing / verification (bcrypt)
- JWT token creation / verification
- Password strength validation
- Token blacklist support for logout
- Rate limiting utilities
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Set

import bcrypt
import jwt
from jwt import PyJWTError

from app.core.config import settings

# In-memory blacklist for logged-out tokens
# Production: use Redis or database
_token_blacklist: Set[str] = set()

class SecurityError(Exception):
    """Base class for security-related errors."""
    pass

class AuthenticationError(SecurityError):
    """Raised when authentication fails."""
    pass

class AuthorizationError(SecurityError):
    """Raised when authorization fails."""
    pass

class PasswordValidationError(SecurityError):
    """Raised when password validation fails."""
    pass

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password as string
        
    Raises:
        SecurityError: If hashing fails
    """
    if not password or len(password) < 8:
        raise PasswordValidationError("Password must be at least 8 characters")
    
    try:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        raise SecurityError(f"Failed to hash password: {e}")

def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password to verify
        hashed_password: Stored hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def validate_password_strength(password: str) -> list[str]:
    """
    Validate password meets security requirements.
    
    Args:
        password: Password to validate
        
    Returns:
        List of validation error messages, empty if password is valid
    """
    errors = []
    
    if not password:
        errors.append("Password is required")
        return errors
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if len(password) > 128:
        errors.append("Password must not exceed 128 characters")
    
    # Check for common weak passwords (simplified)
    weak_passwords = {'password', '12345678', 'qwerty', 'letmein', 'admin'}
    if password.lower() in weak_passwords:
        errors.append("Password is too common, please choose a stronger one")
    
    # Check for complexity requirements
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)
    
    complexity_score = sum([has_upper, has_lower, has_digit, has_special])
    
    if complexity_score < 2:
        errors.append("Password should contain at least 2 of the following: uppercase letters, lowercase letters, numbers, special characters")
    
    return errors

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary with user claims (user_id, email, role, etc.)
        expires_delta: Optional custom expiration time
        
    Returns:
        JWT token as string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def verify_access_token(token: str) -> dict:
    """
    Verify and decode an access token.
    
    Args:
        token: JWT token to verify
        
    Returns:
        Decoded token payload
        
    Raises:
        AuthenticationError: If token is invalid, expired, or blacklisted
    """
    if is_token_blacklisted(token):
        raise AuthenticationError("Token has been revoked")
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        
        if payload.get("type") != "access":
            raise AuthenticationError("Invalid token type")
        
        return payload
    except PyJWTError as e:
        raise AuthenticationError(f"Invalid token: {e}")

def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        data: Dictionary with user claims
        
    Returns:
        JWT refresh token as string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)  # Refresh tokens last 7 days
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def verify_refresh_token(token: str) -> dict:
    """
    Verify and decode a refresh token.
    
    Args:
        token: JWT refresh token
        
    Returns:
        Decoded token payload
        
    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        
        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type")
        
        return payload
    except PyJWTError as e:
        raise AuthenticationError(f"Invalid refresh token: {e}")

def blacklist_token(token: str) -> None:
    """
    Add a token to the blacklist (for logout functionality).
    
    Args:
        token: Token to blacklist
    """
    _token_blacklist.add(token)

def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token is blacklisted.
    
    Args:
        token: Token to check
        
    Returns:
        True if token is blacklisted, False otherwise
    """
    return token in _token_blacklist

def cleanup_blacklisted_tokens() -> None:
    """
    Clean up expired tokens from the blacklist.
    
    Note: This is a simple in-memory cleanup for development.
    In production, use a proper cache with TTL (like Redis).
    """
    global _token_blacklist
    # For now, this is a no-op since we're using in-memory storage
    # In production with Redis, you would implement periodic cleanup
    pass

def generate_password_reset_token(user_id: str) -> str:
    """
    Generate a password reset token.
    
    Args:
        user_id: User ID to generate token for
        
    Returns:
        Password reset token
    """
    data = {
        "user_id": user_id,
        "type": "password_reset",
        "iat": datetime.utcnow(),
    }
    
    expire = datetime.utcnow() + timedelta(hours=1)
    data["exp"] = expire
    
    token = jwt.encode(data, settings.SECRET_KEY, algorithm="HS256")
    return token

def verify_password_reset_token(token: str) -> str:
    """
    Verify a password reset token and return the user ID.
    
    Args:
        token: Password reset token
        
    Returns:
        User ID from token
        
    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        
        if payload.get("type") != "password_reset":
            raise AuthenticationError("Invalid token type")
        
        return payload["user_id"]
    except PyJWTError as e:
        raise AuthenticationError(f"Invalid password reset token: {e}")

# Security constants and configuration
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
REQUIRE_PASSWORD_COMPLEXITY = True
RATE_LIMIT_WINDOW = 300  # 5 minutes
RATE_LIMIT_MAX_ATTEMPTS = 5  # Max login attempts per window