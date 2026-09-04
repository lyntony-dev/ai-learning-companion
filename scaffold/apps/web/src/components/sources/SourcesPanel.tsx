import { FileMagnifyingGlass } from '@phosphor-icons/react';
import type { Citation } from '@/api/types';
import { DEFAULT_COURSE_PACK } from '@/api/courses';
import { SourceCard } from './SourceCard';

interface SourcesPanelProps {
  citations: Citation[];
  highlightedId: number | null;
  registerRef: (id: number, el: HTMLElement | null) => void;
  coursePackId?: string;
}

export function SourcesPanel({
  citations,
  highlightedId,
  registerRef,
  coursePackId = DEFAULT_COURSE_PACK,
}: SourcesPanelProps) {
  if (citations.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center text-[var(--color-fg-muted)]">
        <FileMagnifyingGlass size={22} weight="duotone" />
        <p className="text-sm">暂无引用来源</p>
        <p className="text-xs">提问后,回答依据的课程片段会列在这里。</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 p-3">
      {citations.map((c) => (
        <SourceCard
          key={c.citation_id}
          citation={c}
          coursePackId={coursePackId}
          highlighted={highlightedId === c.citation_id}
          ref={(el) => registerRef(c.citation_id, el)}
        />
      ))}
    </div>
  );
}
