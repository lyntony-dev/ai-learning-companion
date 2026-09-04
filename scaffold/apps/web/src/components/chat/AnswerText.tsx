import { Fragment } from 'react';
import type { Citation } from '@/api/types';

interface AnswerTextProps {
  content: string;
  citations: Citation[];
  onCitationClick: (citationId: number) => void;
}

const MARKER = /\[(\d+)\]/g;

/**
 * 把回答正文里的引用角标 [n] 渲染成可点击按钮,点击联动右侧来源卡。
 * 仅当 n 存在于 citations 中才可点;否则原样保留文本。
 */
export function AnswerText({ content, citations, onCitationClick }: AnswerTextProps) {
  const known = new Set(citations.map((c) => c.citation_id));
  const parts: Array<string | number> = [];
  let last = 0;
  let match: RegExpExecArray | null;

  MARKER.lastIndex = 0;
  while ((match = MARKER.exec(content)) !== null) {
    const n = Number(match[1]);
    if (!known.has(n)) continue;
    if (match.index > last) parts.push(content.slice(last, match.index));
    parts.push(n);
    last = match.index + match[0].length;
  }
  if (last < content.length) parts.push(content.slice(last));

  return (
    <p className="whitespace-pre-wrap text-sm leading-relaxed">
      {parts.map((part, i) =>
        typeof part === 'number' ? (
          <button
            key={i}
            type="button"
            onClick={() => onCitationClick(part)}
            className="mx-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded bg-[var(--color-accent-soft)] px-1 align-super text-[10px] font-semibold text-[var(--color-accent)] transition-colors hover:bg-[var(--color-accent)] hover:text-[var(--color-accent-fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]"
            aria-label={`查看来源 ${part}`}
          >
            {part}
          </button>
        ) : (
          <Fragment key={i}>{part}</Fragment>
        ),
      )}
    </p>
  );
}
