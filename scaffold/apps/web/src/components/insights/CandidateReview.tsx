import { CheckCircle, Sparkle, Trash, XCircle } from '@phosphor-icons/react';
import { useCandidates } from '@/hooks/useCandidates';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/feedback/Skeleton';
import { EmptyState } from '@/components/feedback/EmptyState';
import { ErrorState } from '@/components/feedback/ErrorState';

const DIFFICULTY_LABEL: Record<string, string> = {
  easy: '入门',
  medium: '进阶',
  hard: '挑战',
};

/**
 * 讲师审核候选题(ADR-0006 飞轮):LLM 依 RAG 证据生成的候选题在此逐条通过/驳回。
 * 通过 → approved_by 沉淀为优先出题来源;驳回 → 删除。四态齐备。
 */
export function CandidateReview({ coursePackId }: { coursePackId: string }) {
  const { candidates, loading, error, reload, pendingId, actionError, approve, reject } =
    useCandidates(coursePackId);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle>候选题审核</CardTitle>
            <p className="text-xs text-[var(--color-fg-muted)]">
              系统依课程材料生成的候选练习题。通过后沉淀为优先出题来源,驳回则删除。
            </p>
          </div>
          {!loading && !error ? (
            <Badge tone="accent">{candidates.length} 待审</Badge>
          ) : null}
        </div>
      </CardHeader>
      <CardContent>
        {actionError ? (
          <p className="mb-3 rounded-[var(--radius)] bg-[color-mix(in_srgb,var(--color-unknown)_12%,transparent)] px-3 py-2 text-xs text-[var(--color-unknown)]">
            {actionError}
          </p>
        ) : null}

        {loading ? (
          <div className="flex flex-col gap-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-28" />
            ))}
          </div>
        ) : error ? (
          <div className="h-48">
            <ErrorState message={error} onRetry={reload} />
          </div>
        ) : candidates.length === 0 ? (
          <div className="h-48">
            <EmptyState
              icon={Sparkle}
              title="暂无待审候选题"
              description="学生练习时若题库不足,系统会依课程材料生成候选题并汇集到此,供你审核沉淀。"
            />
          </div>
        ) : (
          <ul className="flex flex-col gap-3">
            {candidates.map((c) => {
              const busy = pendingId === c.question_id;
              return (
                <li
                  key={c.question_id}
                  className="rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4"
                >
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <Badge tone="neutral">{c.topic_name}</Badge>
                    {c.difficulty ? (
                      <Badge tone="accent">{DIFFICULTY_LABEL[c.difficulty] ?? c.difficulty}</Badge>
                    ) : null}
                  </div>
                  <p className="text-sm font-medium text-[var(--color-fg)]">{c.prompt}</p>
                  {c.reference_answer ? (
                    <p className="mt-2 text-xs leading-relaxed text-[var(--color-fg-muted)]">
                      <span className="font-medium">参考答案:</span>
                      {c.reference_answer}
                    </p>
                  ) : null}
                  <div className="mt-3 flex items-center gap-2">
                    <Button
                      size="sm"
                      disabled={busy}
                      onClick={() => approve(c.question_id)}
                    >
                      <CheckCircle size={15} weight="bold" />
                      通过并沉淀
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={busy}
                      onClick={() => reject(c.question_id)}
                    >
                      {busy ? (
                        <XCircle size={15} />
                      ) : (
                        <Trash size={15} />
                      )}
                      驳回
                    </Button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
