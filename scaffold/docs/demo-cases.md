# Demo Cases

## Case 1：LangGraph State 问答

- 用户问题：`LangGraph 为什么需要 State？`
- 预期行为：
  1. Router 识别为课程问答。
  2. Retrieve 命中 LangGraph 相关 chunk。
  3. Evidence Check 返回 `strong`。
  4. Generate 输出带 `[1]` 的回答。
  5. Sources 面板展示 chunk 来源。
  6. Agent Trace 展示完整节点路径。

## Case 2：MCP 工具生态问答

- 用户问题：`MCP Server 在 Agent 系统里负责什么？`
- 预期行为：
  1. 查询 Course Search MCP。
  2. 命中 MCP Server 相关课程材料。
  3. 回答说明工具暴露、资源访问与协议边界。

## Case 3：证据不足降级

- 用户问题：`课程里有没有讲某个不存在的内部概念？`
- 预期行为：
  1. 首次检索证据不足。
  2. 最多触发 1 次 query rewrite + retrieve。
  3. 仍不足时不编造，返回无法基于课程材料确认的说明。
