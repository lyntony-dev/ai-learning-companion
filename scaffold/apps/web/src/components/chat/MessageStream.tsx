import { useEffect, useRef } from 'react';
import { ChatCircleDots } from '@phosphor-icons/react';
import type { UiMessage } from '@/types/view';
import { ChatMessage } from './ChatMessage';

interface MessageStreamProps {
  messages: UiMessage[];
  onCitationClick: (citationId: number) => void;
}

export function MessageStream({ messages, onCitationClick }: MessageStreamProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-surface-2)] text-[var(--color-accent)]">
          <ChatCircleDots size={24} weight="duotone" />
        </div>
        <h2 className="text-base font-semibold">向课程助教提问</h2>
        <p className="max-w-sm text-sm text-[var(--color-fg-muted)]">
          回答会基于课程资料给出,并在右侧列出引用来源与引擎执行轨迹。证据不足时会诚实拒答,不编造页码。
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 px-6 py-5">
      {messages.map((m) => (
        <ChatMessage key={m.id} message={m} onCitationClick={onCitationClick} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
