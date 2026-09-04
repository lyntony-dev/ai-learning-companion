import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Warning } from '@phosphor-icons/react';
import { useChat } from '@/hooks/useChat';
import { ConversationList } from '@/components/chat/ConversationList';
import { MessageStream } from '@/components/chat/MessageStream';
import { ChatInput } from '@/components/chat/ChatInput';
import { RightPanel } from '@/components/layout/RightPanel';

export function StudentPage() {
  const {
    messages,
    conversations,
    conversationId,
    sending,
    error,
    send,
    selectConversation,
    removeConversation,
    loadTrace,
    reset,
  } = useChat();
  const [tab, setTab] = useState('sources');
  const [highlightedId, setHighlightedId] = useState<number | null>(null);
  const sourceRefs = useRef<Map<number, HTMLElement>>(new Map());

  // 右侧面板展示最后一条助手消息的来源/轨迹
  const lastAssistant = useMemo(
    () => [...messages].reverse().find((m) => m.role === 'assistant' && !m.pending),
    [messages],
  );
  const citations = lastAssistant?.citations ?? [];
  const trace = lastAssistant?.trace ?? [];

  // 历史回答:trace 未加载但有 traceId 时,按需懒加载 Agent Trace。
  useEffect(() => {
    if (lastAssistant && !lastAssistant.trace && lastAssistant.traceId) {
      loadTrace(lastAssistant.id);
    }
  }, [lastAssistant, loadTrace]);

  const registerRef = useCallback((id: number, el: HTMLElement | null) => {
    if (el) sourceRefs.current.set(id, el);
    else sourceRefs.current.delete(id);
  }, []);

  const handleCitationClick = useCallback((citationId: number) => {
    setTab('sources');
    setHighlightedId(citationId);
    // 等 Tab 切换渲染后滚动到目标来源卡
    requestAnimationFrame(() => {
      sourceRefs.current.get(citationId)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
    window.setTimeout(() => setHighlightedId(null), 1600);
  }, []);

  return (
    <div className="grid h-full grid-cols-[260px_minmax(420px,1fr)_360px] max-lg:grid-cols-[220px_1fr]">
      {/* 左:会话列表 */}
      <aside className="min-h-0 overflow-y-auto border-r border-[var(--color-border)]">
        <ConversationList
          conversations={conversations}
          activeId={conversationId}
          onSelect={selectConversation}
          onDelete={removeConversation}
          onNew={reset}
        />
      </aside>

      {/* 中:对话 */}
      <section className="flex min-h-0 flex-col">
        <div className="min-h-0 flex-1 overflow-y-auto">
          <MessageStream messages={messages} onCitationClick={handleCitationClick} />
        </div>
        <div className="border-t border-[var(--color-border)] p-4">
          {error ? (
            <div className="mb-2 flex items-center gap-2 rounded-[var(--radius)] border border-[color-mix(in_srgb,var(--color-unknown)_40%,transparent)] bg-[color-mix(in_srgb,var(--color-unknown)_8%,transparent)] px-3 py-2 text-sm text-[var(--color-unknown)]">
              <Warning size={15} weight="fill" />
              <span>{error}</span>
            </div>
          ) : null}
          <ChatInput disabled={sending} onSend={send} />
          <p className="mt-2 text-center text-xs text-[var(--color-fg-muted)]">
            回答由 AI 基于课程资料生成,单次约需十几秒。
          </p>
        </div>
      </section>

      {/* 右:来源 / Trace(小屏隐藏,归后续响应式细化) */}
      <aside className="min-h-0 border-l border-[var(--color-border)] max-lg:hidden">
        <RightPanel
          tab={tab}
          onTabChange={setTab}
          citations={citations}
          trace={trace}
          highlightedId={highlightedId}
          registerRef={registerRef}
        />
      </aside>
    </div>
  );
}
