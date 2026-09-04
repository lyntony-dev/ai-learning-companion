import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, CaretRight } from '@phosphor-icons/react';
import { listCoursePacks } from '@/api/courses';
import { ApiError } from '@/api/client';
import type { CoursePackSummary } from '@/api/types';

export function CoursesPage() {
  const [packs, setPacks] = useState<CoursePackSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    listCoursePacks(ctrl.signal)
      .then((res) => setPacks(res.packs))
      .catch((err) => {
        if (ctrl.signal.aborted) return;
        setError(err instanceof ApiError ? err.message : '课程加载失败');
      });
    return () => ctrl.abort();
  }, []);

  return (
    <div className="mx-auto h-full max-w-3xl overflow-y-auto px-6 py-8">
      <h1 className="mb-1 text-xl font-semibold">课程</h1>
      <p className="mb-6 text-sm text-[var(--color-fg-muted)]">
        选择一门课程进入,查看讲义、课件与示例代码。
      </p>

      {error ? (
        <p className="text-sm text-[var(--color-unknown)]">{error}</p>
      ) : packs === null ? (
        <p className="text-sm text-[var(--color-fg-muted)]">加载中…</p>
      ) : packs.length === 0 ? (
        <p className="text-sm text-[var(--color-fg-muted)]">暂无课程。</p>
      ) : (
        <div className="flex flex-col gap-3">
          {packs.map((pack) => (
            <Link
              key={pack.course_pack_id}
              to={`/courses/${encodeURIComponent(pack.course_pack_id)}`}
              className="group flex items-center gap-4 rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 transition-colors hover:border-[var(--color-accent)]"
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--radius)] bg-[var(--color-accent-soft)] text-[var(--color-accent)]">
                <BookOpen size={20} weight="duotone" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate font-medium">{pack.name}</span>
                <span className="block truncate text-sm text-[var(--color-fg-muted)]">
                  {pack.description}
                </span>
                <span className="mt-1 block text-xs text-[var(--color-fg-muted)]">
                  {pack.course_count} 门课 · {pack.version}
                </span>
              </span>
              <CaretRight
                size={18}
                className="shrink-0 text-[var(--color-fg-muted)] transition-transform group-hover:translate-x-0.5"
              />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
