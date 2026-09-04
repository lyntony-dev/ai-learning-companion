import { Users } from '@phosphor-icons/react';
import { useLearners } from '@/hooks/useLearners';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/feedback/Skeleton';
import { ErrorState } from '@/components/feedback/ErrorState';

interface LearnerListProps {
  coursePackId: string;
  onSelect: (learnerId: string) => void;
}

const PAGE_SIZE = 20;

export function LearnerList({ coursePackId, onSelect }: LearnerListProps) {
  const { data, loading, error, offset, setOffset, reload } = useLearners(coursePackId);

  return (
    <Card>
      <CardHeader>
        <CardTitle>学员列表</CardTitle>
        <p className="text-xs text-[var(--color-fg-muted)]">
          点选查看并修正个体掌握度{data ? ` · 共 ${data.total} 人` : ''}
        </p>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex flex-col gap-2">
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-14 w-full" />
            ))}
          </div>
        ) : error ? (
          <div className="h-48">
            <ErrorState message={error} onRetry={reload} />
          </div>
        ) : data && data.items.length > 0 ? (
          <div className="flex flex-col gap-2">
            {data.items.map((it) => (
              <button
                key={it.learner_id}
                type="button"
                onClick={() => onSelect(it.learner_id)}
                className="flex items-center justify-between gap-3 rounded-[var(--radius)] border border-[var(--color-border)] px-3 py-2.5 text-left transition-colors hover:bg-[var(--color-surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]"
              >
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium">
                    {it.display_name || it.learner_id}
                  </div>
                  <div className="truncate text-xs text-[var(--color-fg-muted)]">{it.learner_id}</div>
                </div>
                <div className="flex shrink-0 gap-1.5">
                  <Badge tone="known">掌握 {it.known}</Badge>
                  <Badge tone="fuzzy">模糊 {it.fuzzy}</Badge>
                  <Badge tone="unknown">未掌握 {it.unknown}</Badge>
                </div>
              </button>
            ))}
            {data.total > PAGE_SIZE ? (
              <div className="mt-1 flex items-center justify-between">
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                >
                  上一页
                </Button>
                <span className="text-xs tabular-nums text-[var(--color-fg-muted)]">
                  {offset + 1} - {Math.min(offset + data.items.length, data.total)} / {data.total}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={offset + PAGE_SIZE >= data.total}
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                >
                  下一页
                </Button>
              </div>
            ) : null}
          </div>
        ) : (
          <div className="flex h-40 flex-col items-center justify-center gap-2 text-center">
            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--color-surface-2)] text-[var(--color-fg-muted)]">
              <Users size={22} weight="duotone" />
            </div>
            <p className="text-sm text-[var(--color-fg-muted)]">
              暂无学员。学生注册并开始学习后会出现在这里。
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
