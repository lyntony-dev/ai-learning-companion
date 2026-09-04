"""密码哈希与轻量签名 token (ADR-0008)。

- 密码:bcrypt(已装),哈希存 LearnerAuth.password_hash。
- token:标准库 hmac+hashlib,格式 `base64url(payload_json).base64url(hmac_sig)`,
  payload 含 learner_id / username / exp(过期时间戳)。零第三方 JWT 依赖,符合轻量取向。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import bcrypt


def hash_password(plain: str) -> str:
    """bcrypt 哈希,返回 utf-8 字符串存库。"""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, password_hash: str) -> bool:
    """校验明文与哈希。哈希非法/为空时安全返回 False。"""
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _b64u_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64u_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def sign_token(
    learner_id: str,
    username: str,
    secret: str,
    ttl_hours: int,
    role: str = "student",
) -> str:
    """签发 `payload.signature` 形式的 token。role 缺省 student(兼容旧签发)。"""
    payload = {
        "learner_id": learner_id,
        "username": username,
        "role": role,
        "exp": int(time.time()) + ttl_hours * 3600,
    }
    payload_b64 = _b64u_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_b64}.{_b64u_encode(sig)}"


def verify_token(token: str, secret: str) -> dict | None:
    """校验签名与过期时间。合法返回 payload dict,否则返回 None。"""
    if not token or "." not in token:
        return None
    payload_b64, sig_b64 = token.rsplit(".", 1)
    expected = hmac.new(
        secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256
    ).digest()
    try:
        provided = _b64u_decode(sig_b64)
    except (ValueError, TypeError):
        return None
    if not hmac.compare_digest(expected, provided):
        return None
    try:
        payload = json.loads(_b64u_decode(payload_b64))
    except (ValueError, TypeError):
        return None
    if not isinstance(payload, dict) or "learner_id" not in payload:
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload
