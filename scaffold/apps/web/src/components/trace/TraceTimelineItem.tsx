import { CheckCircle, XCircle, ArrowsClockwise, Circle, MinusCircle } from '@phosphor-icons/react';
import type { AgentTraceEvent } from '@/api/types';
import { cn } from '@/lib/utils';

function statusIcon(status: string) {
  switch (status) {
    case 'success':
      return <CheckCircle size={16} weight="fill" className="text-[var(--color-known)]" />;
    case 'error':
    case 'refused':
      return <XCircle size={16} weight="fill" className="text-[var(--color-unknown)]" />;
    case 'retry':
      return <ArrowsClockwise size={16} className="text-[var(--color-fuzzy)]" />;
    case 'skipped':
      return <MinusCircle size={16} className="text-[var(--color-fg-muted)]" />;
    default:
      return <Circle size={16} className="text-[var(--color-fg-muted)]" />;
  }
}

export function TraceTimelineItem({ event, last }: { event: AgentTraceEvent; last: boolean }) {
  return (
    <li className="relative flex gap-3 pb-3">
      {!last ? (
        <span className="absolute left-[7px] top-5 h-full w-px bg-[var(--color-border)]" />
      ) : null}
      <span className="z-10 mt-0.5 shrink-0">{statusIcon(event.status)}</span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{event.node_name}</span>
          <span className="text-xs text-[var(--color-fg-muted)]">{event.status}</span>
        </div>
        {event.output_summary ? (
          <p className={cn('mt-0.5 text-xs text-[var(--color-fg-muted)]')}>{event.output_summary}</p>
        ) : null}
      </div>
    </li>
  );
}
