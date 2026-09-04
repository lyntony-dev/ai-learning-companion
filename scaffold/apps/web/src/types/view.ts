import type { AgentTraceEvent, Citation } from '@/api/types';

/** 前端会话视图模型(本轮 MVP 用局部 state 承载)。 */
export interface UiMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  /** 助手消息:证据等级或 "insufficient"(拒答) */
  status?: string;
  citations?: Citation[];
  trace?: AgentTraceEvent[];
  /** 关联的 trace_id(历史 assistant 消息):用于按需懒加载 Agent Trace。 */
  traceId?: string | null;
  /** 助手消息等待后端返回中 */
  pending?: boolean;
  /** 流式进行中当前执行到的节点名(诚实进度,非 token 流) */
  progressNode?: string;
}

export interface UiConversation {
  conversationId: string | null;
  title: string;
  messages: UiMessage[];
}
