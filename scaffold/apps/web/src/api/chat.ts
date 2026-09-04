import { apiDelete, apiGet, apiPost } from './client';
import { getStoredToken } from '@/lib/auth';
import type {
  ChatRequest,
  ChatResponse,
  ConversationListResponse,
  MessageListResponse,
  TraceResponse,
} from './types';

const DEFAULT_USER = 'demo_user';

/**
 * 本轮不传 task_type/learner_answer(后端未暴露,固定走 rag_answer)。
 * 一次真实 invoke 约十几秒、同步无流式。
 */
export function postChat(req: ChatRequest, signal?: AbortSignal): Promise<ChatResponse> {
  const body: ChatRequest = {
    user_id: DEFAULT_USER,
    course_ids: [],
    top_k: 5,
    ...req,
  };
  return apiPost<ChatResponse>('/chat', body, signal);
}

/** 流式进度事件:诚实的节点级进度(非 token 流)。 */
export interface StreamProgress {
  node: string;
  status: string;
}

export interface StreamHandlers {
  onProgress?: (progress: StreamProgress) => void;
  onFinal: (result: ChatResponse) => void;
  onError?: (detail: string) => void;
}

/**
 * SSE 流式问答:逐节点吐真实进度(progress),整图 review 校验后吐 final(已校验回答)。
 * 绝不流式吐未校验 token(与后端铁律一致)。失败/中断由调用方回退到同步 postChat。
 */
export async function streamChat(
  req: ChatRequest,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const body: ChatRequest = { user_id: DEFAULT_USER, course_ids: [], top_k: 5, ...req };
  const token = getStoredToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch('/api/chat/stream', {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`stream_failed_${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sep: number;
    // SSE 记录以空行分隔
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      const raw = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const { event, data } = parseSseBlock(raw);
      if (!data) continue;
      if (event === 'progress') {
        handlers.onProgress?.(data as StreamProgress);
      } else if (event === 'final') {
        handlers.onFinal(data as ChatResponse);
      } else if (event === 'error') {
        handlers.onError?.((data as { detail?: string }).detail ?? '引擎处理出错,请稍后重试。');
      }
    }
  }
}

function parseSseBlock(raw: string): { event: string; data: unknown } {
  let event = 'message';
  let dataLine = '';
  for (const line of raw.split('\n')) {
    if (line.startsWith('event: ')) event = line.slice(7);
    else if (line.startsWith('data: ')) dataLine = line.slice(6);
  }
  return { event, data: dataLine ? JSON.parse(dataLine) : null };
}


export function listConversations(signal?: AbortSignal): Promise<ConversationListResponse> {
  return apiGet<ConversationListResponse>('/conversations', signal);
}

export function listMessages(
  conversationId: string,
  signal?: AbortSignal,
): Promise<MessageListResponse> {
  return apiGet<MessageListResponse>(
    `/conversations/${encodeURIComponent(conversationId)}/messages`,
    signal,
  );
}

/** 历史 Agent Trace 懒加载:按 assistant 消息的 trace_id 取回完整事件。 */
export function getTrace(traceId: string, signal?: AbortSignal): Promise<TraceResponse> {
  return apiGet<TraceResponse>(`/traces/${encodeURIComponent(traceId)}`, signal);
}

/** 删除会话(含其全部消息),返回 204。 */
export function deleteConversation(conversationId: string, signal?: AbortSignal): Promise<void> {
  return apiDelete(`/conversations/${encodeURIComponent(conversationId)}`, signal);
}
