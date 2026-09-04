"""登录/画像服务 (ADR-0008)。

- register:建 Learner(身份主体) + LearnerAuth(凭据) + LearnerProfile(空画像),用户名查重。
- login:校验密码,签发签名 token。
- get_account / update_profile:画像读写。
- auto_profile:自动学习画像——跨课程聚合 Mastery(复用 T 的掌握度语义,不新建存储)。

learner_id 采用 `stu_<username>` 规则,保证与旧 demo_user 访客数据天然隔离且稳定可读。
讲师账号采用 `tea_<username>` 规则,role 携带在 token 内(不落库,业务库无迁移机制);
讲师注册需邀请码(非自由注册),邀请码走 config(dev 占位,生产覆盖)。
"""

from __future__ import annotations

import re

from sqlmodel import select

from app.auth.security import hash_password, sign_token, verify_password
from app.core.config import Settings, get_settings
from app.persistence import (
    Learner,
    LearnerAuth,
    LearnerProfile,
    Mastery,
    MasteryLevel,
    get_session,
    init_business_db,
)

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_\u4e00-\u9fa5]{2,32}$")

STUDENT_PREFIX = "stu_"
TEACHER_PREFIX = "tea_"


def role_of(learner_id: str | None) -> str:
    """由 learner_id 前缀派生角色。讲师 tea_,其余(含访客/学生)为 student。"""
    if learner_id and learner_id.startswith(TEACHER_PREFIX):
        return "teacher"
    return "student"


class AuthError(Exception):
    """登录/注册领域错误。message 直接面向用户。"""


class AuthService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        init_business_db(self._settings)

    # --- 内部 ---

    def _learner_id_for(self, username: str, role: str = "student") -> str:
        prefix = TEACHER_PREFIX if role == "teacher" else STUDENT_PREFIX
        return f"{prefix}{username}"

    def _issue_token(self, learner_id: str, username: str, role: str = "student") -> str:
        return sign_token(
            learner_id,
            username,
            self._settings.auth_token_secret,
            self._settings.auth_token_ttl_hours,
            role=role,
        )

    # --- 注册 / 登录 ---

    def register(
        self,
        username: str,
        password: str,
        display_name: str = "",
        role: str = "student",
        invite_code: str = "",
    ) -> dict:
        username = (username or "").strip()
        if not _USERNAME_RE.match(username):
            raise AuthError("用户名需为 2-32 位字母/数字/下划线/中文")
        if len(password or "") < 6:
            raise AuthError("密码至少 6 位")
        if role not in ("student", "teacher"):
            raise AuthError("角色非法")
        if role == "teacher" and invite_code != self._settings.auth_teacher_invite_code:
            raise AuthError("讲师邀请码错误")

        learner_id = self._learner_id_for(username, role)
        with get_session(self._settings) as session:
            existing = session.exec(
                select(LearnerAuth).where(LearnerAuth.username == username)
            ).first()
            if existing is not None:
                raise AuthError("用户名已被占用")

            display = display_name.strip() or username
            if session.get(Learner, learner_id) is None:
                session.add(Learner(learner_id=learner_id, display_name=display))
            session.add(
                LearnerAuth(
                    learner_id=learner_id,
                    username=username,
                    password_hash=hash_password(password),
                )
            )
            session.add(LearnerProfile(learner_id=learner_id, nickname=display))
            session.commit()

        token = self._issue_token(learner_id, username, role)
        return {
            "learner_id": learner_id,
            "username": username,
            "display_name": display,
            "role": role,
            "token": token,
        }

    def login(self, username: str, password: str) -> dict:
        username = (username or "").strip()
        with get_session(self._settings) as session:
            auth = session.exec(
                select(LearnerAuth).where(LearnerAuth.username == username)
            ).first()
            if auth is None or not verify_password(password, auth.password_hash):
                raise AuthError("用户名或密码错误")
            learner = session.get(Learner, auth.learner_id)
            display = learner.display_name if learner else username

        role = role_of(auth.learner_id)
        token = self._issue_token(auth.learner_id, username, role)
        return {
            "learner_id": auth.learner_id,
            "username": username,
            "display_name": display,
            "role": role,
            "token": token,
        }

    # --- 画像 ---

    def get_account(self, learner_id: str) -> dict:
        """返回身份 + 画像 + 自动学习画像。learner 不存在 → AuthError。"""
        with get_session(self._settings) as session:
            learner = session.get(Learner, learner_id)
            if learner is None:
                raise AuthError("学习者不存在")
            auth = session.exec(
                select(LearnerAuth).where(LearnerAuth.learner_id == learner_id)
            ).first()
            profile = session.get(LearnerProfile, learner_id)
        return {
            "learner_id": learner_id,
            "username": auth.username if auth else "",
            "display_name": learner.display_name,
            "role": role_of(learner_id),
            "profile": self._profile_dict(profile),
            "auto_profile": self.auto_profile(learner_id),
        }

    def update_profile(self, learner_id: str, fields: dict) -> dict:
        """部分更新画像。仅接受白名单字段。返回最新 account。"""
        allowed = {
            "nickname",
            "avatar",
            "background",
            "learning_goal",
            "weekly_hours",
            "preferred_difficulty",
        }
        with get_session(self._settings) as session:
            if session.get(Learner, learner_id) is None:
                raise AuthError("学习者不存在")
            profile = session.get(LearnerProfile, learner_id)
            if profile is None:
                profile = LearnerProfile(learner_id=learner_id)
                session.add(profile)
            for key, value in fields.items():
                if key in allowed and value is not None:
                    setattr(profile, key, value)
            from app.persistence.models import _utcnow

            profile.updated_at = _utcnow()
            session.add(profile)
            session.commit()
        return self.get_account(learner_id)

    def auto_profile(self, learner_id: str) -> dict:
        """自动学习画像:跨课程聚合掌握度(会/模糊/不会计数)。运行时聚合,不持久化。"""
        counts = {MasteryLevel.KNOWN: 0, MasteryLevel.FUZZY: 0, MasteryLevel.UNKNOWN: 0}
        with get_session(self._settings) as session:
            rows = session.exec(
                select(Mastery).where(Mastery.learner_id == learner_id)
            ).all()
        for row in rows:
            if row.level in counts:
                counts[row.level] += 1
        return {
            "known": counts[MasteryLevel.KNOWN],
            "fuzzy": counts[MasteryLevel.FUZZY],
            "unknown": counts[MasteryLevel.UNKNOWN],
            "topics_tracked": len(rows),
        }

    @staticmethod
    def _profile_dict(profile: LearnerProfile | None) -> dict:
        if profile is None:
            return {
                "nickname": "",
                "avatar": "",
                "background": "",
                "learning_goal": "",
                "weekly_hours": 0,
                "preferred_difficulty": "",
            }
        return {
            "nickname": profile.nickname,
            "avatar": profile.avatar,
            "background": profile.background,
            "learning_goal": profile.learning_goal,
            "weekly_hours": profile.weekly_hours,
            "preferred_difficulty": profile.preferred_difficulty,
        }
