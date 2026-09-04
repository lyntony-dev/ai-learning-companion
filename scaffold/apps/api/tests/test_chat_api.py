from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.engine.learner_model import EmptyLearnerModel
from app.main import app
from app.routes.chat import get_learner_model, get_retriever


class _FakeRetriever:
    """注入替身:返回强证据 chunk,离线跑通 /chat StateGraph。"""

    def retrieve(self, course_pack_id, query, course_ids=None, top_k=5):
        return [
            {
                "chunk_id": "mock_chunk_001",
                "text": "LangGraph State 用于在多个节点之间传递上下文与中间结果。",
                "score": 0.9,
                "metadata": {
                    "course_id": "langgraph_multiagent",
                    "section": "StateGraph",
                    "source_path": "slides/slide_06.html",
                    "slide_no": 6,
                },
            }
        ]


def _override_settings(db_path: Path):
    def override():  # type: ignore[no-untyped-def]
        from app.core.config import Settings

        # LLM 用 mock provider,产出含 [1] 引用的确定性回答
        return Settings(DATABASE_URL=f"sqlite:///{db_path}", LLM_PROVIDER="mock")

    return override


def test_chat_endpoint_returns_answer_and_persists_summaries(tmp_path: Path) -> None:
    db_path = tmp_path / "app.sqlite"
    app.dependency_overrides[get_settings] = _override_settings(db_path)
    app.dependency_overrides[get_retriever] = lambda: _FakeRetriever()
    app.dependency_overrides[get_learner_model] = lambda: EmptyLearnerModel()
    try:
        client = TestClient(app)
        response = client.post(
            "/api/chat",
            json={"question": "LangGraph State 是什么？", "user_id": "demo_user"},
        )
        body = response.json()

        conversations_response = client.get("/api/conversations", params={"user_id": "demo_user"})
        messages_response = client.get(f"/api/conversations/{body['conversation_id']}/messages")
        trace_response = client.get(f"/api/traces/{body['trace_id']}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert body["status"] == "strong"
    assert len(body["citations"]) == 1
    assert body["citations"][0]["chunk_id"] == "mock_chunk_001"
    assert body["conversation_id"].startswith("conv_")
    assert body["trace_id"].startswith("trace_")

    assert conversations_response.status_code == 200
    conversations = conversations_response.json()["conversations"]
    assert len(conversations) == 1
    assert conversations[0]["conversation_id"] == body["conversation_id"]

    assert messages_response.status_code == 200
    messages = messages_response.json()["messages"]
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[0]["content_summary"] == "LangGraph State 是什么？"
    # 全保真:content 存全文(user),assistant 带 trace_id 关联本轮 trace。
    assert messages[0]["content"] == "LangGraph State 是什么？"
    assert messages[1]["content"] == body["answer"]
    assert messages[1]["trace_id"] == body["trace_id"]
    assert messages[1]["citations"][0]["chunk_id"] == "mock_chunk_001"

    assert trace_response.status_code == 200
    node_names = [event["node_name"] for event in trace_response.json()["events"]]
    # 真 StateGraph 纵切:C/D 装饰 + Router + 问答子图
    assert node_names[0] == "personalize_opener"
    assert node_names[1] == "router"
    assert node_names[-1] == "closing_advice"
    assert "retrieve" in node_names
    assert "evidence_check" in node_names
    assert "answer" in node_names
    assert "final" in node_names


import json


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    """把 SSE 文本拆成 (event, data) 列表。"""
    events: list[tuple[str, dict]] = []
    for block in text.strip().split("\n\n"):
        if not block.strip():
            continue
        event = ""
        data = ""
        for line in block.splitlines():
            if line.startswith("event: "):
                event = line[len("event: ") :]
            elif line.startswith("data: "):
                data = line[len("data: ") :]
        events.append((event, json.loads(data) if data else {}))
    return events


def test_chat_stream_emits_progress_then_validated_final(tmp_path: Path) -> None:
    db_path = tmp_path / "app.sqlite"
    app.dependency_overrides[get_settings] = _override_settings(db_path)
    app.dependency_overrides[get_retriever] = lambda: _FakeRetriever()
    app.dependency_overrides[get_learner_model] = lambda: EmptyLearnerModel()
    try:
        client = TestClient(app)
        response = client.post(
            "/api/chat/stream",
            json={"question": "LangGraph State 是什么？", "user_id": "demo_user"},
        )
        events = _parse_sse(response.text)

        final = next(data for event, data in events if event == "final")
        # 校验后的 final 必须能被后端持久化路径复原
        messages = client.get(
            f"/api/conversations/{final['conversation_id']}/messages"
        ).json()["messages"]
        trace = client.get(f"/api/traces/{final['trace_id']}").json()
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    progress_nodes = [data["node"] for event, data in events if event == "progress"]
    # 诚实的节点级进度:真实节点按序上报
    assert progress_nodes[0] == "personalize_opener"
    assert "router" in progress_nodes
    assert "retrieve" in progress_nodes
    assert "answer" in progress_nodes

    # final 携带已校验回答 + 引用,且落库与同步路径一致
    assert final["status"] == "strong"
    assert final["citations"][0]["chunk_id"] == "mock_chunk_001"
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[1]["content"] == final["answer"]
    assert messages[1]["trace_id"] == final["trace_id"]
    assert trace["trace_id"] == final["trace_id"]


def test_delete_conversation_removes_conversation_and_messages(tmp_path: Path) -> None:
    db_path = tmp_path / "app.sqlite"
    app.dependency_overrides[get_settings] = _override_settings(db_path)
    app.dependency_overrides[get_retriever] = lambda: _FakeRetriever()
    app.dependency_overrides[get_learner_model] = lambda: EmptyLearnerModel()
    try:
        client = TestClient(app)
        created = client.post(
            "/api/chat",
            json={"question": "LangGraph State 是什么？", "user_id": "demo_user"},
        ).json()
        conversation_id = created["conversation_id"]

        delete_response = client.delete(f"/api/conversations/{conversation_id}")
        conversations = client.get(
            "/api/conversations", params={"user_id": "demo_user"}
        ).json()["conversations"]
        messages = client.get(
            f"/api/conversations/{conversation_id}/messages"
        ).json()["messages"]
    finally:
        app.dependency_overrides.clear()

    assert delete_response.status_code == 204
    # 会话与其消息都应被清除
    assert conversations == []
    assert messages == []


def test_get_trace_returns_404_for_missing_trace(tmp_path: Path) -> None:
    db_path = tmp_path / "app.sqlite"
    app.dependency_overrides[get_settings] = _override_settings(db_path)
    try:
        client = TestClient(app)
        response = client.get("/api/traces/missing_trace")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "trace_not_found"}
