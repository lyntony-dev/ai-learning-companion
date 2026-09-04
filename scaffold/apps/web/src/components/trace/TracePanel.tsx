import { TreeStructure } from '@phosphor-icons/react';
import type { AgentTraceEvent } from '@/api/types';
import { TraceTimelineItem } from './TraceTimelineItem';

export function TracePanel({ trace }: { trace: AgentTraceEvent[] }) {
  if (trace.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center text-[var(--color-fg-muted)]">
        <TreeStructure size={22} weight="duotone" />
        <p className="text-sm">暂无执行轨迹</p>
        <p className="text-xs">提问后,引擎每个节点的执行过程会列在这里。</p>
      </div>
    );
  }

  return (
    <ol className="flex flex-col p-4">
      {trace.map((event, i) => (
        <TraceTimelineItem
          key={`${event.node_name}-${i}`}
          event={event}
          last={i === trace.length - 1}
        />
      ))}
    </ol>
  );
}
