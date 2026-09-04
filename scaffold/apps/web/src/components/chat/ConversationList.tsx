import { Plus, ChatCircleText, Trash } from '@phosphor-icons/react';
import type { ConversationSummary } from '@/api/types';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface ConversationListProps {
  conversations: ConversationSummary[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onNew: () => void;
}

/**
 * 会话列表:由后端持久化(GET /api/conversations),刷新不丢。
 * 点击切换会拉回该会话历史(摘要版);悬停/聚焦时可删除会话。
 */
export function ConversationList({
  conversations,
  activeId,
  onSelect,
  onDelete,
  onNew,
}: ConversationListProps) {
  return (
    <div className="flex h-full flex-col gap-2 p-3">
      <Button variant="outline" size="sm" className="w-full justify-start" onClick={onNew}>
        <Plus size={16} />
        新会话
      </Button>

      <div className="mt-1 flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
        {conversations.length === 0 ? (
          <p className="px-3 py-2 text-xs text-[var(--color-fg-muted)]">
            还没有会话,提出第一个问题开始吧。
          </p>
        ) : (
          conversations.map((c) => {
            const active = c.conversation_id === activeId;
            return (
              <div
                key={c.conversation_id}
                className={cn(
                  'group flex items-center gap-1 rounded-[var(--radius)] pr-1 transition-colors',
                  active
                    ? 'bg-[var(--color-surface-2)]'
                    : 'hover:bg-[var(--color-surface-2)]',
                )}
              >
                <button
                  type="button"
                  onClick={() => onSelect(c.conversation_id)}
                  aria-current={active}
                  className={cn(
                    'flex min-w-0 flex-1 items-center gap-2 rounded-[var(--radius)] px-3 py-2 text-left text-sm transition-colors',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]',
                    active
                      ? 'text-[var(--color-fg)]'
                      : 'text-[var(--color-fg-muted)] group-hover:text-[var(--color-fg)]',
                  )}
                >
                  <ChatCircleText size={15} className="shrink-0" />
                  <span className="truncate">{c.title || '新会话'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => onDelete(c.conversation_id)}
                  aria-label={`删除会话 ${c.title || '新会话'}`}
                  className={cn(
                    'shrink-0 rounded-[var(--radius)] p-1.5 text-[var(--color-fg-muted)] transition-opacity',
                    'opacity-0 group-hover:opacity-100 focus-visible:opacity-100',
                    'hover:text-[var(--color-unknown)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]',
                  )}
                >
                  <Trash size={15} />
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
