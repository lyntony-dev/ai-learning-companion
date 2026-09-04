"""学生登录/身份包 (ADR-0008)。

轻量账号体系:用户名+密码(bcrypt 哈希)+ 标准库 HMAC 自签 token(非 JWT 库)。
未登录仍可用 demo_user 访客态;登录后 token 内 learner_id 具权威性。
"""

from app.auth.deps import resolve_learner_id
from app.auth.security import (
    hash_password,
    sign_token,
    verify_password,
    verify_token,
)
from app.auth.service import AuthError, AuthService

__all__ = [
    "resolve_learner_id",
    "hash_password",
    "verify_password",
    "sign_token",
    "verify_token",
    "AuthService",
    "AuthError",
]
