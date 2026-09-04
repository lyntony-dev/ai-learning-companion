import { motion } from 'motion/react';
import type { UiMessage } from '@/types/view';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { AnswerText } from './AnswerText';
import { PendingAnswer } from './PendingAnswer';

interface ChatMessageProps {
  message: UiMessage;
  onCitationClick: (citationId: number) => void;
}

function statusLabel(status?: string): { text: string; tone: 'known' | 'fuzzy' | 'unknown' } | null {
  if (!status) return null;
  if (status === 'insufficient') return { text: '证据不足 · 已拒答', tone: 'unknown' };
  if (status === 'strong') return { text: '证据充分', tone: 'known' };
  if (status === 'weak') return { text: '证据较弱', tone: 'fuzzy' };
  return null;
}

export function ChatMessage({ message, onCitationClick }: ChatMessageProps) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="flex justify-end"
      >
        <div className="max-w-[80%] rounded-[var(--radius)] bg-[var(--color-accent)] px-4 py-2.5 text-sm leading-relaxed text-[var(--color-accent-fg)]">
          {message.content}
        </div>
      </motion.div>
    );
  }

  if (message.pending) {
    return <PendingAnswer activeNode={message.progressNode} />;
  }

  const badge = statusLabel(message.status);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="flex justify-start"
    >
      <div
        className={cn(
          'max-w-[85%] rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3',
        )}
      >
        {badge ? (
          <div className="mb-2">
            <Badge tone={badge.tone}>{badge.text}</Badge>
          </div>
        ) : null}
        <AnswerText
          content={message.content}
          citations={message.citations ?? []}
          onCitationClick={onCitationClick}
        />
      </div>
    </motion.div>
  );
}
