"""Pydantic schemas for authentication and user identity."""

from typing import Optional

from pydantic import BaseModel, Field


class UserSignupRequest(BaseModel):
    """Signup payload."""

    username: str = Field(..., min_length=3, max_length=64)
    email: str
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=255)


class UserLoginRequest(BaseModel):
    """Login payload."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Access token response."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Safe user profile response."""

    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
