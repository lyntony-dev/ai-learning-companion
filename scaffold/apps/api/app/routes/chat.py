import json
import time
import uuid
from collections.abc import Iterator

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.agent.models import AgentTraceEvent, Citation
from app.auth.deps import resolve_learner_id
from app.core.config import Settings, get_settings
from app.course_pack import CoursePackLoader
from app.db.migrations import apply_migrations
from app.db.sqlite import connect
from app.engine.learner_model import EmptyLearnerModel, LearnerModel, SqlLearnerModel
from app.engine.orchestration.main_graph import build_main_graph, initial_state
from app.engine.retrieval import Retriever, VectorStoreRetriever
from app.llm import get_llm_client
from app.persistence import init_business_db
from app.models.conversation import ConversationRecord, MessageRecord
from app.models.trace import TraceEventRecord, TraceRecord
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.trace_repository import TraceRepository
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationListResponse,
    ConversationSummary,
    MessageListResponse,
    MessageSummary,
    TraceEventSummary,
    TraceResponse,
)

router = APIRouter(prefix="/api", tags=["chat"])

# 默认课程包(单课程包 MVP;多包时由请求或会话上下文决定)
DEFAULT_COURSE_PACK_ID = "ai_agent"


def get_retriever(settings: Settings = Depends(get_settings)) -> Retriever:
    """检索器依赖。测试可通过 app.dependency_overrides 注入替身。"""
    return VectorStoreRetriever(settings)


def get_learner_model(settings: Settings = Depends(get_settings)) -> LearnerModel:
    """Learner Model 依赖(B/C/D)。加载失败时降级为空模型,保证问答可用。"""
    try:
        init_business_db(settings)
        pack = CoursePackLoader().load(DEFAULT_COURSE_PACK_ID)
        return SqlLearnerModel(pack, settings=settings)
    except Exception:
        return EmptyLearnerModel()


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    retriever: Retriever = Depends(get_retriever),
    learner_model: LearnerModel = Depends(get_learner_model),
) -> ChatResponse:
    started_at = time.perf_counter()
    conversation_id = payload.conversation_id or f"conv_{uuid.uuid4().hex}"
    trace_id = f"trace_{uuid.uuid4().hex}"
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    # 登录身份优先(token),否则回落到请求体 user_id(访客 demo_user)
    user_id = resolve_learner_id(payload.user_id, request.headers.get("authorization"), settings)

    # 真 LangGraph 主图:C/D 装饰 → Router → 问答子图 → B 掌握度更新(ADR-0001/0004)
    graph = build_main_graph(retriever, llm=get_llm_client(settings), learner_model=learner_model)
    result = graph.invoke(
        initial_state(
            query=payload.question,
            course_pack_id=DEFAULT_COURSE_PACK_ID,
            learner_id=user_id,
            course_ids=payload.course_ids,
            top_k=payload.top_k,
            max_retry=settings.max_retrieval_retry,
            max_generate_retry=settings.max_generate_retry,
        )
    )
    total_latency_ms = round((time.perf_counter() - started_at) * 1000)

    answer, status, citations, trace_events = _extract_result(result)
    _persist_turn(
        settings,
        conversation_id=conversation_id,
        trace_id=trace_id,
        request_id=request_id,
        user_id=user_id,
        question=payload.question,
        answer=answer,
        status=status,
        citations=citations,
        trace_events=trace_events,
        total_latency_ms=total_latency_ms,
    )

    return ChatResponse(
        conversation_id=conversation_id,
        trace_id=trace_id,
        answer=answer,
        status=status,
        citations=citations,
        trace=trace_events,
    )


@router.post("/chat/stream")
def chat_stream(
    payload: ChatRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    retriever: Retriever = Depends(get_retriever),
    learner_model: LearnerModel = Depends(get_learner_model),
) -> StreamingResponse:
    """诚实的节点级进度流(SSE / ADR 铁律:不做假流式)。

    逐个节点吐真实进度事件(personalize_opener→router→qa→learner_update→closing_advice),
    待整图跑完、review 节点校验后,再吐一个 `final` 事件携带已校验的 answer/citations/trace_id。
    绝不流式吐未经 review 的原始 token(review 可能拒答/降级),避免暴露未校验文本。
    持久化与同步 /chat 完全一致;同步 /chat 保持不变,访客路径零回归。
    """
    started_at = time.perf_counter()
    conversation_id = payload.conversation_id or f"conv_{uuid.uuid4().hex}"
    trace_id = f"trace_{uuid.uuid4().hex}"
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    user_id = resolve_learner_id(payload.user_id, request.headers.get("authorization"), settings)

    graph = build_main_graph(retriever, llm=get_llm_client(settings), learner_model=learner_model)

    def event_stream() -> Iterator[str]:
        latest: dict = {}
        seen: set[str] = set()
        try:
            # stream_mode="values":每个节点执行后回吐累积后的完整 state
            for chunk in graph.stream(
                initial_state(
                    query=payload.question,
                    course_pack_id=DEFAULT_COURSE_PACK_ID,
                    learner_id=user_id,
                    course_ids=payload.course_ids,
                    top_k=payload.top_k,
                    max_retry=settings.max_retrieval_retry,
                    max_generate_retry=settings.max_generate_retry,
                ),
                stream_mode="values",
            ):
                latest = chunk
                # 从累积 trace 中挑出尚未上报的真实节点事件
                for event in chunk.get("trace", []):
                    node = event.get("node", "")
                    key = f"{node}:{event.get('status', '')}:{event.get('output_summary', '')}"
                    if key in seen:
                        continue
                    seen.add(key)
                    yield _sse("progress", {"node": node, "status": event.get("status", "success")})
        except Exception:  # noqa: BLE001 引擎异常降级为可读错误事件
            yield _sse("error", {"detail": "引擎处理出错,请稍后重试。"})
            return

        total_latency_ms = round((time.perf_counter() - started_at) * 1000)
        answer, status, citations, trace_events = _extract_result(latest)
        _persist_turn(
            settings,
            conversation_id=conversation_id,
            trace_id=trace_id,
            request_id=request_id,
            user_id=user_id,
            question=payload.question,
            answer=answer,
            status=status,
            citations=citations,
            trace_events=trace_events,
            total_latency_ms=total_latency_ms,
        )
        yield _sse(
            "final",
            {
                "conversation_id": conversation_id,
                "trace_id": trace_id,
                "answer": answer,
                "status": status,
                "citations": [c.model_dump() for c in citations],
                "trace": [e.model_dump() for e in trace_events],
            },
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(event: str, data: dict) -> str:
    """构造一条 SSE 记录(event + JSON data)。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _extract_result(
    result: dict,
) -> tuple[str, str, list[Citation], list[AgentTraceEvent]]:
    """从主图结果中抽取回答、证据等级、引用与 Trace 事件(同步/流式共用)。"""
    answer = result.get("answer", "")
    status = "insufficient" if result.get("refused") else result.get("evidence_level", "strong")
    citations = [
        Citation(
            citation_id=c.get("citation_id", i + 1),
            chunk_id=c.get("chunk_id", ""),
            course_id=c.get("course_id", ""),
            course_name=c.get("course_id", ""),
            section=c.get("section", ""),
            source_path=c.get("source_path", ""),
            slide_no=c.get("slide_no"),
            anchor_type=c.get("anchor_type", "none"),
            anchor_value=c.get("anchor_value", ""),
        )
        for i, c in enumerate(result.get("citations", []))
    ]
    trace_events = [
        AgentTraceEvent(
            node_name=e.get("node", ""),
            status=e.get("status", "success"),
            input_summary=e.get("input_summary", ""),
            output_summary=e.get("output_summary", ""),
            metadata=e.get("metadata", {}),
        )
        for e in result.get("trace", [])
    ]
    return answer, status, citations, trace_events


def _persist_turn(
    settings: Settings,
    *,
    conversation_id: str,
    trace_id: str,
    request_id: str,
    user_id: str,
    question: str,
    answer: str,
    status: str,
    citations: list[Citation],
    trace_events: list[AgentTraceEvent],
    total_latency_ms: int,
) -> None:
    """落库一轮问答:会话/消息/Trace(同步与流式路径完全一致)。"""
    with connect(settings) as connection:
        apply_migrations(connection)
        conversation_repository = ConversationRepository(connection)
        trace_repository = TraceRepository(connection)

        conversation_repository.create_conversation(
            ConversationRecord(
                conversation_id=conversation_id,
                user_id=user_id,
                title=_summarize(question, limit=60) or "新会话",
            )
        )
        conversation_repository.append_message(
            MessageRecord(
                message_id=f"msg_{uuid.uuid4().hex}",
                conversation_id=conversation_id,
                role="user",
                content_summary=_summarize(question),
                content=question,
            )
        )
        conversation_repository.append_message(
            MessageRecord(
                message_id=f"msg_{uuid.uuid4().hex}",
                conversation_id=conversation_id,
                role="assistant",
                content_summary=_summarize(answer),
                content=answer,
                trace_id=trace_id,
                citations=[citation.model_dump() for citation in citations],
            )
        )
        trace_repository.create_trace(
            TraceRecord(
                trace_id=trace_id,
                conversation_id=conversation_id,
                request_id=request_id,
                user_id=user_id,
                status="success" if status != "insufficient" else "degraded",
                total_latency_ms=total_latency_ms,
            )
        )
        for index, event in enumerate(trace_events, start=1):
            trace_repository.append_event(
                TraceEventRecord(
                    event_id=f"{trace_id}_event_{index:03d}",
                    trace_id=trace_id,
                    node_name=event.node_name,
                    status=event.status,
                    input_summary=event.input_summary,
                    output_summary=event.output_summary,
                    metadata=event.metadata,
                )
            )


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(
    user_id: str = "demo_user",
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> ConversationListResponse:
    user_id = resolve_learner_id(user_id, authorization, settings)
    with connect(settings) as connection:
        apply_migrations(connection)
        conversations = ConversationRepository(connection).list_conversations(user_id=user_id)

    return ConversationListResponse(
        conversations=[ConversationSummary(**conversation.model_dump()) for conversation in conversations]
    )


@router.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse)
def list_messages(
    conversation_id: str,
    settings: Settings = Depends(get_settings),
) -> MessageListResponse:
    with connect(settings) as connection:
        apply_migrations(connection)
        messages = ConversationRepository(connection).list_messages(conversation_id=conversation_id)

    return MessageListResponse(messages=[MessageSummary(**message.model_dump()) for message in messages])


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: str,
    settings: Settings = Depends(get_settings),
) -> None:
    with connect(settings) as connection:
        apply_migrations(connection)
        ConversationRepository(connection).delete_conversation(conversation_id=conversation_id)


@router.get("/traces/{trace_id}", response_model=TraceResponse)
def get_trace(
    trace_id: str,
    settings: Settings = Depends(get_settings),
) -> TraceResponse:
    with connect(settings) as connection:
        apply_migrations(connection)
        events = TraceRepository(connection).list_events(trace_id=trace_id)

    if not events:
        raise HTTPException(status_code=404, detail="trace_not_found")

    return TraceResponse(
        trace_id=trace_id,
        events=[TraceEventSummary(**event.model_dump()) for event in events],
    )


def _summarize(text: str, limit: int = 200) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}..."
