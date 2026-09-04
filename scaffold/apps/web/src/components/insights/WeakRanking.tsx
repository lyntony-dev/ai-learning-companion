import type { TopicInsight } from '@/api/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface WeakRankingProps {
  ranking: TopicInsight[];
}

function weakScore(t: TopicInsight): number {
  const total = t.known + t.fuzzy + t.unknown;
  if (total === 0) return 0;
  return Math.round(((t.unknown + t.fuzzy * 0.5) / total) * 100);
}

export function WeakRanking({ ranking }: WeakRankingProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>薄弱知识点排行</CardTitle>
        <p className="text-xs text-[var(--color-fg-muted)]">按未掌握 + 半数模糊占比排序</p>
      </CardHeader>
      <CardContent>
        {ranking.length === 0 ? (
          <p className="py-8 text-center text-sm text-[var(--color-fg-muted)]">暂无薄弱点数据</p>
        ) : (
          <ol className="flex flex-col gap-2.5">
            {ranking.map((t, i) => {
              const score = weakScore(t);
              return (
                <li key={t.topic_id} className="flex items-center gap-3">
                  <span className="w-5 shrink-0 text-right text-sm font-medium tabular-nums text-[var(--color-fg-muted)]">
                    {i + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <span className="truncate text-sm">{t.name}</span>
                      <span className="shrink-0 text-xs tabular-nums text-[var(--color-fg-muted)]">
                        {score}%
                      </span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-[var(--color-surface-2)]">
                      <div
                        className="h-full rounded-full bg-[var(--color-unknown)]"
                        style={{ width: `${score}%` }}
                      />
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}
