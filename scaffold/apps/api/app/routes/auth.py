"""学生登录/画像路由 (ADR-0008)。

  - POST /api/auth/register   注册(建身份+凭据+空画像),返回 token
  - POST /api/auth/login      登录,返回 token
  - GET  /api/auth/me         当前登录学生的身份+画像+自动画像(需 Bearer token)
  - PATCH /api/auth/me        更新画像(需 Bearer token)

未登录不影响其它路由的访客态(demo_user);此处 /me 强制要求登录。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth.deps import current_learner_id
from app.auth.service import AuthError, AuthService
from app.core.config import Settings, get_settings
from app.schemas.auth import (
    AccountResponse,
    AuthTokenResponse,
    LoginRequest,
    RegisterRequest,
    UpdateProfileRequest,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_auth_service(settings: Settings = Depends(get_settings)) -> AuthService:
    return AuthService(settings=settings)


def require_learner_id(learner_id: str | None = Depends(current_learner_id)) -> str:
    """强制登录:无合法 token → 401。"""
    if not learner_id:
        raise HTTPException(status_code=401, detail="unauthorized: 需要登录")
    return learner_id


@router.post("/register", response_model=AuthTokenResponse)
def register(
    payload: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> AuthTokenResponse:
    try:
        result = service.register(
            payload.username,
            payload.password,
            payload.display_name,
            role=payload.role,
            invite_code=payload.invite_code,
        )
    except AuthError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AuthTokenResponse(**result)


@router.post("/login", response_model=AuthTokenResponse)
def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> AuthTokenResponse:
    try:
        result = service.login(payload.username, payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return AuthTokenResponse(**result)


@router.get("/me", response_model=AccountResponse)
def me(
    learner_id: str = Depends(require_learner_id),
    service: AuthService = Depends(get_auth_service),
) -> AccountResponse:
    try:
        return AccountResponse(**service.get_account(learner_id))
    except AuthError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/me", response_model=AccountResponse)
def update_me(
    payload: UpdateProfileRequest,
    learner_id: str = Depends(require_learner_id),
    service: AuthService = Depends(get_auth_service),
) -> AccountResponse:
    try:
        return AccountResponse(**service.update_profile(learner_id, payload.to_fields()))
    except AuthError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
