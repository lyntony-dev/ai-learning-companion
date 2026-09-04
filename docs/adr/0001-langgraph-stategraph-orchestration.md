# ADR-0001：编排层用真正的 LangGraph StateGraph 重写

- 状态：已接受
- 日期：2026-07-16

## 背景

已有脚手架 `scaffold/apps/api/app/agent/graph.py` 的 `CourseTutorAgent.run()` 是**手写的顺序方法链**：

```python
state = self._router(state)
state = self._query_rewrite(state)
state = self._retrieve(state)
state = self._evidence_check(state)
state = self._generate(state)
state = self._review(state)
state = self._final(state)
```

它没有引入 `langgraph` 依赖，没有 `StateGraph`、条件边、真实循环或 `END` 条件。`evidence_check` 与 `review` 的"分叉/重试/拒答"逻辑都被拉直成无分支的直线执行。

PRD 的 **GRAPH-001 是硬性验收标准**：代码中必须存在 State、Node、Edge、Conditional Edge 和 END 条件；GRAPH-002/003 要求真实的 Query Rewrite 重试与 `max_retry` 退出。已有 `tech_arch_design.xml` 5.3 也画了带条件分叉和 `Rewrite→Retrieve` 回环的工作流图。因此现状与 PRD 及自身架构文档都不一致。

## 决策

用真正的 `langgraph.StateGraph` 重写编排层：

- `TutorState`（TypedDict）作为显式共享状态，字段对齐 `tech_arch_design.xml` 5.2 与 PRD 8.2。
- 现有 7 个 `_node` 方法改造为 LangGraph 节点函数。
- `evidence_check` 用 `add_conditional_edges` 分叉为 `{证据足→generate / 不足且未超限→query_rewrite / 不足且已超限→refuse}`。
- `review` 用 `add_conditional_edges` 分叉为 `{通过→final / 可修→generate / 不可修→refuse}`。
- `query_rewrite → retrieve` 形成受 `retry_count < max_retry` 约束的真实回环。
- 终点接 `END`。

## 权衡

- **成本**：引入 `langgraph` 依赖，开发复杂度高于手写串行链；节点函数需遵循 LangGraph 的状态合并约定。
- **收益**：满足 PRD 硬验收；获得可观测轨迹、条件边、循环控制；作为教学示范项目，"显式状态机"本身就是核心教学价值——手写串行链是反面教材。
- **被否决的方案**：保留手写链只在文档里"声称"是工作流。否决理由：无法通过 GRAPH-001 验收，且违背项目教学目标。

## 影响

- `scaffold/apps/api/app/agent/graph.py` 需重写；`AgentState`（Pydantic model）迁移为 `TutorState`（TypedDict）或桥接。
- 单测 `tests/test_agent_graph.py` 需相应更新，验证条件边与重试退出。
