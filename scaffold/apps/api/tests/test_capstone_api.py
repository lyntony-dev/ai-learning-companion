"""结课项目立项 + 个性化清单 (F) HTTP 端点测试 (DESIGN §4)。

覆盖:
  - GET  project:未立项 → 向导态(has_project=false,里程碑仅给作业说明,无清单)
  - POST project:立项 → 生成项目卡 + 每里程碑个性化清单;里程碑重置 not_started
  - PATCH item:勾选清单项 → 派生里程碑状态 + 写回 milestone_progress;全勾 → passed
  - PATCH item:未知 item → 404;未立项时 PATCH → 404
  - 缺课程包 → 404

用真实 tmp 业务库 + mock LLM(默认 provider),离线可跑:
mock LLM 输出不是合法计划 JSON,服务走 deliverable 拆解的保底清单,清单项稳定可勾选。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.persistence import init_business_db, reset_engine

REPO_ROOT = Path(__file__).resolve().parents[4]
AI_AGENT_EXISTS = (REPO_ROOT / "data" / "course_packs" / "ai_agent" / "manifest.yaml").exists()

pytestmark = pytest.mark.skipif(not AI_AGENT_EXISTS, reason="ai_agent 课程包不存在")


@pytest.fixture()
def business_db(tmp_path, monkeypatch):
    db = tmp_path / "business.sqlite"
    monkeypatch.setenv("BUSINESS_DB_URL", f"sqlite:///{db}")
    reset_engine()
    from app.core.config import Settings

    settings = Settings(_env_file=None, BUSINESS_DB_URL=f"sqlite:///{db}")
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


def _get_project(client, learner_id: str) -> dict:
    r = client.get("/api/capstone/courses/ai_agent/project", params={"learner_id": learner_id})
    assert r.status_code == 200
    return r.json()


def test_get_project_wizard_state_when_not_created(client) -> None:
    body = _get_project(client, "u1")
    assert body["has_project"] is False
    assert body["card"] is None
    assert body["total"] >= 1
    assert len(body["milestones"]) == body["total"]
    # 向导态:里程碑仅有作业说明(name/deliverable/hint),无清单、状态全 not_started
    assert all(m["status"] == "not_started" for m in body["milestones"])
    assert all(m["items"] == [] for m in body["milestones"])
    # 引导内容:项目说明书(供学生端立项前阅读)
    assert body["overview"].strip()
    assert body["final_deliverable"].strip()
    first = body["milestones"][0]
    assert first["deliverable"].strip()
    assert "hint" in first
    assert body["all_passed"] is False


def test_create_project_generates_card_and_checklist(client) -> None:
    r = client.post(
        "/api/capstone/courses/ai_agent/project",
        json={
            "learner_id": "u2",
            "goal": "做一个基于我的课程笔记回答问题的个人学习助手",
            "audience": "笔记很多但搜不准的开发者",
            "difficulty": "担心检索召回不准",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["has_project"] is True
    assert body["card"] is not None
    assert body["card"]["title"].strip()
    # 每个里程碑都生成了可勾选清单(mock LLM → deliverable 保底拆解)
    assert body["total"] == len(body["milestones"])
    for m in body["milestones"]:
        assert len(m["items"]) >= 1
        for it in m["items"]:
            assert it["id"]
            assert it["text"].strip()
            assert it["checked"] is False
        assert m["status"] == "not_started"
    assert body["passed_count"] == 0
    assert body["all_passed"] is False


def test_toggle_item_advances_milestone_status(client) -> None:
    created = client.post(
        "/api/capstone/courses/ai_agent/project",
        json={"learner_id": "u3", "goal": "一个能查天气并给穿衣建议的助手"},
    ).json()
    first = created["milestones"][0]
    items = first["items"]
    assert len(items) >= 1

    # 勾选第一项 → 里程碑进入 in_progress(除非只有一项则直接 passed)
    r1 = client.patch(
        f"/api/capstone/courses/ai_agent/project/items/{items[0]['id']}",
        json={"learner_id": "u3", "checked": True},
    )
    assert r1.status_code == 200
    m1 = next(m for m in r1.json()["milestones"] if m["milestone_id"] == first["milestone_id"])
    assert m1["status"] in {"in_progress", "passed"}
    assert m1["items"][0]["checked"] is True

    # 勾完该里程碑所有项 → passed
    for it in items:
        r = client.patch(
            f"/api/capstone/courses/ai_agent/project/items/{it['id']}",
            json={"learner_id": "u3", "checked": True},
        )
        assert r.status_code == 200
    final = r.json()
    m_final = next(
        m for m in final["milestones"] if m["milestone_id"] == first["milestone_id"]
    )
    assert m_final["status"] == "passed"
    assert final["passed_count"] >= 1
    assert final["current_milestone_id"] != first["milestone_id"]


def test_toggle_unknown_item_returns_404(client) -> None:
    client.post(
        "/api/capstone/courses/ai_agent/project",
        json={"learner_id": "u4", "goal": "一个代码评审助手"},
    )
    r = client.patch(
        "/api/capstone/courses/ai_agent/project/items/nope-00000000",
        json={"learner_id": "u4", "checked": True},
    )
    assert r.status_code == 404
    assert "item_not_found" in r.json()["detail"]


def test_toggle_before_project_created_returns_404(client) -> None:
    r = client.patch(
        "/api/capstone/courses/ai_agent/project/items/whatever-00000000",
        json={"learner_id": "u5", "checked": True},
    )
    assert r.status_code == 404
    assert "project_not_found" in r.json()["detail"]


def test_project_course_not_found(client) -> None:
    r = client.get(
        "/api/capstone/courses/no_such_pack/project", params={"learner_id": "u1"}
    )
    assert r.status_code == 404
    assert "course_pack_not_found" in r.json()["detail"]
