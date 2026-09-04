import { useCallback, useEffect, useRef, useState } from 'react';
import {
  deleteConversation,
  getTrace,
  listConversations,
  listMessages,
  postChat,
  streamChat,
} from '@/api/chat';
import { ApiError } from '@/api/client';
import type {
  AgentTraceEvent,
  ChatResponse,
  Citation,
  ConversationSummary,
  MessageSummary,
} from '@/api/types';
import type { UiMessage } from '@/types/view';

let idSeq = 0;
const nextId = () => `m${Date.now()}-${idSeq++}`;

const ACTIVE_KEY = 'tutor.activeConversationId';

interface UseChatResult {
  messages: UiMessage[];
  conversationId: string | null;
  conversations: ConversationSummary[];
  sending: boolean;
  loadingHistory: boolean;
  error: string | null;
  send: (question: string) => void;
  selectConversation: (id: string) => void;
  removeConversation: (id: string) => void;
  loadTrace: (messageId: string) => void;
  reset: () => void;
}

/**
 * 会话状态:发送优先走 SSE 流式 /api/chat/stream(诚实节点级进度),
 * 流式不可用时回退到同步 /api/chat。会话与消息由后端持久化。
 * 刷新后经 localStorage 记住的 conversation_id 从后端拉回历史。
 * 全保真恢复(002 起):历史消息带全文 content 与 assistant 的 trace_id,
 * 回答全文直接恢复;Agent Trace 按需经 GET /api/traces/{id} 懒加载。
 */
export function useChat(): UseChatResult {
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const refreshConversations = useCallback((signal?: AbortSignal) => {
    return listConversations(signal)
      .then((res) => setConversations(res.conversations))
      .catch(() => {
        /* 列表拉取失败不阻塞问答,静默降级 */
      });
  }, []);

  const loadMessages = useCallback((id: string, signal?: AbortSignal) => {
    setLoadingHistory(true);
    return listMessages(id, signal)
      .then((res) => {
        setMessages(res.messages.map(toUiMessage));
        setConversationId(id);
        localStorage.setItem(ACTIVE_KEY, id);
      })
      .catch((err) => {
        if (signal?.aborted) return;
        // 历史会话已不存在:清掉记忆,回到空态
        if (err instanceof ApiError && err.status === 404) {
          localStorage.removeItem(ACTIVE_KEY);
        }
      })
      .finally(() => setLoadingHistory(false));
  }, []);

  // 挂载:拉会话列表,并恢复上次活跃会话
  useEffect(() => {
    const ctrl = new AbortController();
    refreshConversations(ctrl.signal);
    const saved = localStorage.getItem(ACTIVE_KEY);
    if (saved) loadMessages(saved, ctrl.signal);
    return () => ctrl.abort();
  }, [refreshConversations, loadMessages]);

  const send = useCallback(
    (question: string) => {
      const trimmed = question.trim();
      if (!trimmed || sending) return;

      setError(null);
      setSending(true);

      const userMsg: UiMessage = { id: nextId(), role: 'user', content: trimmed };
      const pendingId = nextId();
      const pendingMsg: UiMessage = { id: pendingId, role: 'assistant', content: '', pending: true };
      setMessages((prev) => [...prev, userMsg, pendingMsg]);

      const controller = new AbortController();
      abortRef.current = controller;

      // final:用已校验回答填充 pending 气泡
      const applyFinal = (res: ChatResponse) => {
        setConversationId(res.conversation_id);
        localStorage.setItem(ACTIVE_KEY, res.conversation_id);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === pendingId
              ? {
                  ...m,
                  content: res.answer,
                  status: res.status,
                  citations: res.citations,
                  trace: res.trace,
                  pending: false,
                  progressNode: undefined,
                }
              : m,
          ),
        );
        void refreshConversations();
      };

      const applyError = (err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        let detail = '回答生成失败,请重试。';
        if (err instanceof ApiError) {
          detail = err.status >= 500 ? `引擎处理出错(HTTP ${err.status}),请稍后重试。` : err.detail;
        }
        setError(detail);
        setMessages((prev) => prev.filter((m) => m.id !== pendingId));
      };

      const done = () => {
        setSending(false);
        abortRef.current = null;
      };

      let gotFinal = false;
      streamChat(
        { question: trimmed, conversation_id: conversationId },
        {
          onProgress: ({ node }) => {
            // 诚实的节点级进度:仅更新 pending 气泡的进度标签,不吐未校验文本
            setMessages((prev) =>
              prev.map((m) => (m.id === pendingId ? { ...m, progressNode: node } : m)),
            );
          },
          onFinal: (res) => {
            gotFinal = true;
            applyFinal(res);
          },
          onError: (detail) => {
            setError(detail);
            setMessages((prev) => prev.filter((m) => m.id !== pendingId));
          },
        },
        controller.signal,
      )
        .catch((err: unknown) => {
          if (err instanceof DOMException && err.name === 'AbortError') return;
          if (gotFinal) return;
          // 流式不可用:回退到同步 /api/chat,保证问答可用(诚实降级)
          return postChat({ question: trimmed, conversation_id: conversationId }, controller.signal)
            .then(applyFinal)
            .catch(applyError);
        })
        .finally(done);
    },
    [conversationId, sending, refreshConversations],
  );

  const selectConversation = useCallback(
    (id: string) => {
      if (id === conversationId || sending) return;
      abortRef.current?.abort();
      setError(null);
      void loadMessages(id);
    },
    [conversationId, sending, loadMessages],
  );

  // 删除会话:乐观从列表移除;若删的是当前会话,回到空态。
  const removeConversation = useCallback(
    (id: string) => {
      setConversations((prev) => prev.filter((c) => c.conversation_id !== id));
      if (id === conversationId) {
        setMessages([]);
        setConversationId(null);
        localStorage.removeItem(ACTIVE_KEY);
      }
      deleteConversation(id)
        .catch(() => setError('删除会话失败,请重试。'))
        .finally(() => void refreshConversations());
    },
    [conversationId, refreshConversations],
  );

  // 历史 assistant 消息的 Agent Trace 懒加载:按 traceId 拉回并填充,已有则跳过。
  const loadTrace = useCallback((messageId: string) => {
    setMessages((prev) => {
      const target = prev.find((m) => m.id === messageId);
      if (!target || target.trace || !target.traceId) return prev;
      const traceId = target.traceId;
      getTrace(traceId)
        .then((res) => {
          const trace = res.events.map(toTraceEvent);
          setMessages((cur) =>
            cur.map((m) => (m.id === messageId ? { ...m, trace } : m)),
          );
        })
        .catch(() => {
          /* trace 拉取失败静默降级,不阻塞历史浏览 */
        });
      return prev;
    });
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setConversationId(null);
    setError(null);
    setSending(false);
    localStorage.removeItem(ACTIVE_KEY);
  }, []);

  return {
    messages,
    conversationId,
    conversations,
    sending,
    loadingHistory,
    error,
    send,
    selectConversation,
    removeConversation,
    loadTrace,
    reset,
  };
}

/** 后端消息 → 前端视图消息。全保真:content 全文 + assistant 的 trace_id。 */
function toUiMessage(m: MessageSummary): UiMessage {
  const role = m.role === 'user' ? 'user' : 'assistant';
  const citations =
    role === 'assistant' ? m.citations.map((c) => c as unknown as Citation) : undefined;
  return {
    id: m.message_id,
    role,
    // 全文优先,回退摘要(兼容 002 之前的旧行)
    content: m.content ?? m.content_summary,
    citations,
    traceId: role === 'assistant' ? m.trace_id ?? null : null,
  };
}

/** 后端 TraceEventSummary → TracePanel 渲染用的 AgentTraceEvent(取其子集)。 */
function toTraceEvent(e: {
  node_name: string;
  status: string;
  input_summary: string;
  output_summary: string;
  metadata: Record<string, string | number | boolean | null>;
}): AgentTraceEvent {
  return {
    node_name: e.node_name,
    status: e.status,
    input_summary: e.input_summary,
    output_summary: e.output_summary,
    metadata: e.metadata,
  };
}
