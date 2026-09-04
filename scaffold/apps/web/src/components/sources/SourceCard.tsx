import { forwardRef } from 'react';
import { Eye, FileText } from '@phosphor-icons/react';
import type { Citation } from '@/api/types';
import { usePreview } from '@/components/preview/preview-context';
import { cn } from '@/lib/utils';

interface SourceCardProps {
  citation: Citation;
  coursePackId: string;
  highlighted?: boolean;
}

export const SourceCard = forwardRef<HTMLElement, SourceCardProps>(
  ({ citation, coursePackId, highlighted }, ref) => {
    const { open } = usePreview();
    // source_path 相对 materials/(或课件 courseware/),与 /api/courses/{id} 同一命名空间。
    const canPreview = Boolean(citation.source_path);
    // heading 锚点来自结构化课件(CoursewareDoc v1),预览走 courseware 命名空间。
    const isCourseware = citation.anchor_type === 'heading';

    const inner = (
      <>
        <div className="mb-1.5 flex items-center gap-2">
          <span className="flex h-5 min-w-5 items-center justify-center rounded bg-[var(--color-accent-soft)] px-1 text-xs font-semibold text-[var(--color-accent)]">
            {citation.citation_id}
          </span>
          <span className="truncate text-sm font-medium">{citation.course_name}</span>
          {canPreview ? (
            <Eye
              size={14}
              className="ml-auto shrink-0 text-[var(--color-fg-muted)] opacity-0 transition-opacity group-hover:opacity-100"
            />
          ) : null}
        </div>
        <p className="mb-1 text-sm text-[var(--color-fg)]">{citation.section}</p>
        <div className="flex items-center gap-1.5 text-xs text-[var(--color-fg-muted)]">
          <FileText size={13} />
          <span className="truncate">{citation.source_path}</span>
          {citation.slide_no != null ? (
            <span className="shrink-0">· 第 {citation.slide_no} 页</span>
          ) : null}
        </div>
      </>
    );

    const className = cn(
      'group block w-full rounded-[var(--radius)] border bg-[var(--color-surface)] p-3 text-left transition-colors',
      highlighted
        ? 'border-[var(--color-accent)] bg-[var(--color-accent-soft)]'
        : 'border-[var(--color-border)]',
      canPreview && 'hover:border-[var(--color-accent)]',
    );

    if (canPreview) {
      return (
        <button
          ref={ref as React.Ref<HTMLButtonElement>}
          type="button"
          onClick={() =>
            open({
              coursePackId,
              relPath: citation.source_path,
              title: `${citation.course_name} · ${citation.section}`,
              kind: isCourseware ? 'courseware' : 'material',
              slideNo: citation.slide_no,
              anchorType: citation.anchor_type,
              anchorValue: citation.anchor_value,
            })
          }
          className={className}
          title="在应用内预览原始资料"
        >
          {inner}
        </button>
      );
    }

    return (
      <div ref={ref as React.Ref<HTMLDivElement>} className={className}>
        {inner}
      </div>
    );
  },
);
SourceCard.displayName = 'SourceCard';
