# PR 5：LangGraph 主链路骨架

## 范围

PR 5 增加课程助教主 Agent 编排骨架，对齐目标链路：

```text
Router → Query Rewrite → Retrieve → Evidence Check → Generate → Review → Final
```

当前实现位于：

- `apps/api/app/agent/models.py`
- `apps/api/app/agent/retriever.py`
- `apps/api/app/agent/graph.py`

## 设计说明

PR 5 采用确定性本地骨架，不接入真实 LLM，不强制引入 LangGraph 运行时依赖。这样做的目标是先稳定节点边界、状态结构、引用结构与 trace 结构，后续再将节点函数迁移到真实 LangGraph graph。

## 核心状态

`AgentState` 包含：

- `request`
- `route`
- `rewritten_query`
- `retrieved_chunks`
- `evidence_level`
- `evidence_score`
- `draft_answer`
- `final_answer`
- `citations`
- `trace`
- `retrieval_attempts`
- `generation_attempts`

## 节点职责

1. `Router`
   - 判断是否进入课程问答路径。
2. `QueryRewrite`
   - 进行轻量查询规范化。
3. `Retrieve`
   - 通过 `CourseSearchRetriever` 获取课程 chunk。
4. `EvidenceCheck`
   - 根据最高 score 标记 `strong`、`weak`、`insufficient`。
5. `Generate`
   - 基于检索 chunk 生成带 `[1]` 引用的确定性答案。
6. `Review`
   - 检查证据充足时是否包含引用。
7. `Final`
   - 输出最终答案、结构化 citation 与 trace。

## 当前限制

- 不接入真实 LLM。
- 不接入真实 LangGraph runtime。
- 不通过网络调用 MCP Server。
- `CourseSearchRetriever` 仍是本地 adapter/mock 边界。
- evidence scoring 仍是轻量规则，后续需结合 retrieval score、关键词覆盖、metadata match 等因素。

## 后续演进

1. 将节点迁移到真实 LangGraph `StateGraph`。
2. 将 `CourseSearchRetriever` 替换为 MCP client adapter。
3. 增加 Evidence insufficient 时的一次 Query Rewrite + Retrieve retry。
4. 增加 Review failure 时的一次 Generate retry。
5. 将 trace event 写入 `TraceRepository`。
6. 接入真实 LLM provider 与 prompt version 管理。
