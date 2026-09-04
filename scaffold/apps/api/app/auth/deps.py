"""身份解析依赖 (ADR-0008)。

resolve_learner_id:
  - 有合法 Bearer token → 以 token 内 learner_id 为准(登录身份具权威性)。
  - 否则 → 回落到调用方传入的 fallback(通常是请求参数默认的 demo_user 访客态)。

这样既保住"打开即用"的访客体验,又让登录用户的数据自动归属本人。
"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from app.core.config import Settings, get_settings
from app.auth.security import verify_token


def _payload_from_header(authorization: str | None, settings: Settings) -> dict | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return verify_token(authorization[7:].strip(), settings.auth_token_secret)


def current_learner_id(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> str | None:
    """从 Authorization: Bearer <token> 解析出 learner_id。无/非法 token 返回 None。"""
    payload = _payload_from_header(authorization, settings)
    return payload.get("learner_id") if payload else None


def current_identity(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> dict | None:
    """解析出完整身份 payload(learner_id/username/role)。无/非法 token 返回 None。

    role 优先取 token 内字段;缺省(旧 token)按 learner_id 前缀派生,兜底 student。
    """
    payload = _payload_from_header(authorization, settings)
    if payload is None:
        return None
    from app.auth.service import role_of

    return {
        "learner_id": payload.get("learner_id"),
        "username": payload.get("username", ""),
        "role": payload.get("role") or role_of(payload.get("learner_id")),
    }


def require_teacher(identity: dict | None = Depends(current_identity)) -> dict:
    """讲师专属守卫:无 token → 401;非讲师 → 403。返回讲师身份。"""
    if identity is None:
        raise HTTPException(status_code=401, detail="unauthorized: 需要登录")
    if identity.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="forbidden: 需要讲师身份")
    return identity


def resolve_learner_id(fallback: str, authorization: str | None, settings: Settings) -> str:
    """token 身份优先,否则用 fallback(访客/请求参数默认值)。"""
    payload = _payload_from_header(authorization, settings)
    if payload is not None and payload.get("learner_id"):
        return payload["learner_id"]
    return fallback
