"""学生登录/画像 API schema (ADR-0008)。"""

from __future__ import annotations

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str = ""
    role: str = "student"  # student | teacher
    invite_code: str = ""  # 讲师注册必填(邀请码)


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthTokenResponse(BaseModel):
    learner_id: str
    username: str
    display_name: str
    role: str = "student"
    token: str


class ProfileFields(BaseModel):
    nickname: str = ""
    avatar: str = ""
    background: str = ""
    learning_goal: str = ""
    weekly_hours: int = 0
    preferred_difficulty: str = ""


class AutoProfile(BaseModel):
    known: int = 0
    fuzzy: int = 0
    unknown: int = 0
    topics_tracked: int = 0


class AccountResponse(BaseModel):
    learner_id: str
    username: str
    display_name: str
    role: str = "student"
    profile: ProfileFields
    auto_profile: AutoProfile


class UpdateProfileRequest(BaseModel):
    """部分更新;None 字段不改。"""

    nickname: str | None = None
    avatar: str | None = None
    background: str | None = None
    learning_goal: str | None = None
    weekly_hours: int | None = None
    preferred_difficulty: str | None = None

    def to_fields(self) -> dict:
        return {k: v for k, v in self.model_dump().items() if v is not None}
