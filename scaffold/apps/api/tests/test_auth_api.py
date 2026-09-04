"""学生登录 + 画像 (ADR-0008) HTTP 端点测试。

覆盖:
  - register:建身份+凭据+空画像,返回 token;用户名查重 → 422;弱密码/非法用户名 → 422
  - login:正确密码返回 token;错误密码 → 401
  - GET /me:需 token,返回身份+画像+自动画像;无 token → 401
  - PATCH /me:更新画像白名单字段,再读回一致
  - token 身份贯穿:带 Bearer token 的 capstone 立项,数据归属 token 内 learner_id 而非请求体
  - 未登录访客态:capstone 不带 token 仍走请求体 learner_id(demo 体验不破坏)

用真实 tmp 业务库,离线可跑(bcrypt 本地哈希,token 本地签名)。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.persistence import init_business_db, reset_engine


@pytest.fixture()
def business_db(tmp_path, monkeypatch):
    db = tmp_path / "business.sqlite"
    monkeypatch.setenv("BUSINESS_DB_URL", f"sqlite:///{db}")
    reset_engine()
    from app.core.config import Settings

    settings = Settings(
        _env_file=None,
        BUSINESS_DB_URL=f"sqlite:///{db}",
        AUTH_TOKEN_SECRET="test-secret",
        AUTH_TEACHER_INVITE_CODE="secret-invite",
    )
    init_business_db(settings)
    yield settings
    reset_engine()


@pytest.fixture()
def client(business_db):
    from app.core.config import get_settings
    from app.main import app

    app.dependency_overrides[get_settings] = lambda: business_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _register(client, username="alice", password="secret1", display_name="Alice") -> dict:
    r = client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "display_name": display_name},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_register_returns_token_and_learner_id(client) -> None:
    body = _register(client)
    assert body["learner_id"] == "stu_alice"
    assert body["username"] == "alice"
    assert body["display_name"] == "Alice"
    assert body["token"]


def test_register_duplicate_username_rejected(client) -> None:
    _register(client)
    r = client.post("/api/auth/register", json={"username": "alice", "password": "secret1"})
    assert r.status_code == 422
    assert "已被占用" in r.json()["detail"]


def test_register_weak_password_rejected(client) -> None:
    r = client.post("/api/auth/register", json={"username": "bob", "password": "123"})
    assert r.status_code == 422


def test_register_invalid_username_rejected(client) -> None:
    r = client.post("/api/auth/register", json={"username": "a", "password": "secret1"})
    assert r.status_code == 422


def test_login_ok_and_wrong_password(client) -> None:
    _register(client)
    ok = client.post("/api/auth/login", json={"username": "alice", "password": "secret1"})
    assert ok.status_code == 200
    assert ok.json()["learner_id"] == "stu_alice"

    bad = client.post("/api/auth/login", json={"username": "alice", "password": "nope"})
    assert bad.status_code == 401


def test_me_requires_token(client) -> None:
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_returns_profile_and_auto_profile(client) -> None:
    token = _register(client)["token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["learner_id"] == "stu_alice"
    assert body["profile"]["nickname"] == "Alice"
    # 自动画像:新用户无掌握度记录
    assert body["auto_profile"]["topics_tracked"] == 0


def test_update_profile_persists(client) -> None:
    token = _register(client)["token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.patch(
        "/api/auth/me",
        headers=headers,
        json={"learning_goal": "成为 Agent 工程师", "weekly_hours": 12, "background": "后端"},
    )
    assert r.status_code == 200
    prof = r.json()["profile"]
    assert prof["learning_goal"] == "成为 Agent 工程师"
    assert prof["weekly_hours"] == 12
    assert prof["background"] == "后端"

    # 再读回一致
    again = client.get("/api/auth/me", headers=headers).json()["profile"]
    assert again["learning_goal"] == "成为 Agent 工程师"
    assert again["weekly_hours"] == 12


def test_invalid_token_treated_as_unauthenticated(client) -> None:
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer garbage.sig"})
    assert r.status_code == 401


def test_token_identity_overrides_request_body_learner_id(client) -> None:
    """带 token 的 capstone 立项应归属 token 内 learner_id,忽略请求体 learner_id。"""
    token = _register(client)["token"]
    headers = {"Authorization": f"Bearer {token}"}
    # 请求体故意传 impostor,token 身份应覆盖
    r = client.post(
        "/api/capstone/courses/ai_agent/project",
        headers=headers,
        json={"learner_id": "impostor", "goal": "一个代码评审助手"},
    )
    assert r.status_code == 200, r.text

    # token 身份 stu_alice 能读到自己的项目
    mine = client.get(
        "/api/capstone/courses/ai_agent/project",
        headers=headers,
        params={"learner_id": "impostor"},
    )
    assert mine.status_code == 200
    assert mine.json()["has_project"] is True

    # impostor(无 token)看不到该项目 → 仍是向导态
    other = client.get(
        "/api/capstone/courses/ai_agent/project",
        params={"learner_id": "impostor"},
    )
    assert other.status_code == 200
    assert other.json()["has_project"] is False


def test_guest_without_token_uses_request_learner_id(client) -> None:
    """不带 token 时访客态保留:capstone 立项归属请求体 learner_id。"""
    r = client.post(
        "/api/capstone/courses/ai_agent/project",
        json={"learner_id": "demo_user", "goal": "一个天气助手"},
    )
    assert r.status_code == 200
    got = client.get(
        "/api/capstone/courses/ai_agent/project",
        params={"learner_id": "demo_user"},
    )
    assert got.json()["has_project"] is True


# --- 讲师账号 + 角色 (梯队一) ---


def test_teacher_register_requires_invite_code(client) -> None:
    # 缺邀请码 → 422
    bad = client.post(
        "/api/auth/register",
        json={"username": "prof", "password": "secret1", "role": "teacher"},
    )
    assert bad.status_code == 422
    assert "邀请码" in bad.json()["detail"]

    # 正确邀请码 → 成功,learner_id 走 tea_ 前缀、role=teacher
    ok = client.post(
        "/api/auth/register",
        json={
            "username": "prof",
            "password": "secret1",
            "role": "teacher",
            "invite_code": "secret-invite",
        },
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["learner_id"] == "tea_prof"
    assert body["role"] == "teacher"


def test_teacher_login_carries_role(client) -> None:
    client.post(
        "/api/auth/register",
        json={
            "username": "prof",
            "password": "secret1",
            "role": "teacher",
            "invite_code": "secret-invite",
        },
    )
    r = client.post("/api/auth/login", json={"username": "prof", "password": "secret1"})
    assert r.status_code == 200
    assert r.json()["role"] == "teacher"
    assert r.json()["learner_id"] == "tea_prof"


def test_student_cannot_access_insights(client) -> None:
    """学生 token 打讲师专属 insights → 403;无 token → 401。"""
    token = _register(client)["token"]
    forbidden = client.get(
        "/api/insights/courses/ai_agent",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert forbidden.status_code == 403
    assert client.get("/api/insights/courses/ai_agent").status_code == 401


def test_teacher_can_access_insights(client) -> None:
    reg = client.post(
        "/api/auth/register",
        json={
            "username": "prof",
            "password": "secret1",
            "role": "teacher",
            "invite_code": "secret-invite",
        },
    ).json()
    r = client.get(
        "/api/insights/courses/ai_agent",
        headers={"Authorization": f"Bearer {reg['token']}"},
    )
    assert r.status_code == 200
    assert r.json()["course_pack_id"] == "ai_agent"
