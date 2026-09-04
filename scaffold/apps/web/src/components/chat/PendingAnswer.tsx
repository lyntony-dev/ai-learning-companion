import { useEffect, useState } from 'react';
import { CircleNotch } from '@phosphor-icons/react';
import { Skeleton } from '@/components/feedback/Skeleton';
import { cn } from '@/lib/utils';

const STAGES = [
  { key: 'retrieve', label: '检索课程资料' },
  { key: 'answer', label: '生成回答' },
  { key: 'review', label: '证据评审' },
];

/** 真实节点名 → 展示阶段下标(诚实映射,非计时臆测)。 */
const NODE_STAGE: Record<string, number> = {
  personalize_opener: 0,
  router: 0,
  qa: 0,
  retrieve: 0,
  evidence_check: 1,
  answer: 1,
  review: 2,
  learner_update: 2,
  closing_advice: 2,
  final: 2,
};

interface PendingAnswerProps {
  /** 流式回传的真实当前节点名;有值时按真实进度点亮阶段,无值时回落到计时示意。 */
  activeNode?: string;
}

/**
 * 等待期占位:优先用 SSE 流回传的真实节点点亮阶段;流式不可用时,
 * 回落到按节奏推进的示意进度 + 匹配最终布局的骨架屏。不做假流式/假逐字。
 */
export function PendingAnswer({ activeNode }: PendingAnswerProps) {
  const [tick, setTick] = useState(0);

  useEffect(() => {
    // 仅在没有真实节点进度时,按节奏推进示意阶段(停在最后一阶段)。
    if (activeNode) return;
    const timer = setInterval(() => {
      setTick((s) => (s < STAGES.length - 1 ? s + 1 : s));
    }, 3500);
    return () => clearInterval(timer);
  }, [activeNode]);

  const stage = activeNode ? (NODE_STAGE[activeNode] ?? 0) : tick;

  return (
    <div className="flex justify-start">
      <div className="w-[85%] max-w-[85%] rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3">
        <div className="mb-3 flex items-center gap-2 text-xs font-medium text-[var(--color-fg-muted)]">
          <CircleNotch size={14} className="animate-spin" />
          <span>{activeNode ? '引擎工作中(实时进度)' : '引擎工作中'}</span>
        </div>

        <ol className="mb-3 flex flex-col gap-1.5">
          {STAGES.map((s, i) => {
            const done = i < stage;
            const active = i === stage;
            return (
              <li
                key={s.key}
                className={cn(
                  'flex items-center gap-2 text-xs',
                  done && 'text-[var(--color-known)]',
                  active && 'text-[var(--color-fg)]',
                  !done && !active && 'text-[var(--color-fg-muted)] opacity-50',
                )}
              >
                <span
                  className={cn(
                    'h-1.5 w-1.5 rounded-full',
                    done && 'bg-[var(--color-known)]',
                    active && 'animate-pulse bg-[var(--color-accent)]',
                    !done && !active && 'bg-[var(--color-border)]',
                  )}
                />
                {s.label}
              </li>
            );
          })}
        </ol>

        <div className="flex flex-col gap-2">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-[92%]" />
          <Skeleton className="h-3 w-[70%]" />
        </div>
      </div>
    </div>
  );
}
