"""
RegimeX API v1 — Authentication Endpoints
=========================================
Exposes secure user registration, credential authentication (login), and
authenticated-user profile resolution.

Architectural Rule:
- Routes remain strictly thin presentation boundaries.
- No password hashing, JWT encoding/decoding, or SQL query manipulation in route functions.
- All orchestration is delegated to the injected AuthenticationService.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, status

from app.api.v1.models import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
)
from app.core.dependencies import AuthServiceDep, CurrentUserDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description=(
        "Registers a new user identity with a canonical normalized email and "
        "memory-hard Argon2id password hash. Rejects duplicate emails with HTTP 409 Conflict."
    ),
)
async def register_user(
    request: RegisterRequest,
    auth_service: AuthServiceDep,
) -> RegisterResponse:
    """Register a new user account with secure credentials."""
    user_dto = await auth_service.register(
        email=request.email,
        password=request.password,
    )
    return RegisterResponse(
        user=UserResponse(
            id=user_dto.id,
            email=user_dto.email,
            is_active=user_dto.is_active,
            created_at=user_dto.created_at,
        )
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and receive access token",
    description=(
        "Authenticates a user by email and password, issuing a signed, short-lived "
        "JWT access token. Generic failure semantics prevent account enumeration."
    ),
)
async def login_user(
    request: LoginRequest,
    auth_service: AuthServiceDep,
) -> LoginResponse:
    """Authenticate user credentials and issue a signed JWT access token."""
    login_result = await auth_service.login(
        email=request.email,
        password=request.password,
    )
    return LoginResponse(
        access_token=login_result.access_token,
        token_type=login_result.token_type,
        expires_in=login_result.expires_in,
        user=UserResponse(
            id=login_result.user.id,
            email=login_result.user.email,
            is_active=login_result.user.is_active,
            created_at=login_result.user.created_at,
        ),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user identity",
    description=(
        "Returns the safe identity representation for the currently authenticated user. "
        "Requires a valid Authorization: Bearer <token> header."
    ),
)
async def get_current_user_profile(
    current_user: CurrentUserDep,
) -> UserResponse:
    """Resolve and return current authenticated user principal."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )
