import { MagnifyingGlass } from '@phosphor-icons/react';
import { useMemo, useState, type FormEvent } from 'react';
import { DEFAULT_COURSE_PACK } from '@/api/insights';
import { useInsights } from '@/hooks/useInsights';
import { useMetrics } from '@/hooks/useMetrics';
import type { MilestoneInsight, TopicInsight } from '@/api/types';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/feedback/Skeleton';
import { ErrorState } from '@/components/feedback/ErrorState';
import { OverviewBar } from '@/components/insights/OverviewBar';
import { MasteryMatrix } from '@/components/insights/MasteryMatrix';
import { WeakRanking } from '@/components/insights/WeakRanking';
import { MilestoneFunnel } from '@/components/insights/MilestoneFunnel';
import { LearnerList } from '@/components/insights/LearnerList';
import { LearnerDrawer } from '@/components/insights/LearnerDrawer';
import { CandidateReview } from '@/components/insights/CandidateReview';
import { MetricsPanel } from '@/components/insights/MetricsPanel';

function avgMasteryPct(topics: TopicInsight[]): number {
  let known = 0;
  let total = 0;
  for (const t of topics) {
    known += t.known;
    total += t.known + t.fuzzy + t.unknown;
  }
  return total === 0 ? 0 : Math.round((known / total) * 100);
}

function milestonePassPct(milestones: MilestoneInsight[]): number {
  let passed = 0;
  let total = 0;
  for (const m of milestones) {
    passed += m.passed;
    total += m.passed + m.in_progress + m.not_started;
  }
  return total === 0 ? 0 : Math.round((passed / total) * 100);
}

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-[74px]" />
        ))}
      </div>
      <Skeleton className="h-64" />
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
    </div>
  );
}

export function TeacherPage() {
  const coursePackId = DEFAULT_COURSE_PACK;
  const { data, loading, error, reload } = useInsights(coursePackId);
  const metricsState = useMetrics(coursePackId);
  const [learnerId, setLearnerId] = useState<string | null>(null);
  const [lookupValue, setLookupValue] = useState('');

  const overview = useMemo(() => {
    if (!data) return null;
    return {
      learnerCount: data.learner_count,
      weakCount: data.weak_ranking.length,
      avgMastery: avgMasteryPct(data.topics),
      milestonePassRate: milestonePassPct(data.milestones),
    };
  }, [data]);

  const handleLookup = (e: FormEvent) => {
    e.preventDefault();
    const id = lookupValue.trim();
    if (id) setLearnerId(id);
  };

  return (
    <div className="mx-auto h-full max-w-5xl overflow-y-auto px-6 py-6">
      <div className="mb-5 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold">教学洞察看板</h1>
          <p className="text-sm text-[var(--color-fg-muted)]">课程包:{coursePackId} · 演示模式</p>
        </div>
        <form onSubmit={handleLookup} className="flex items-center gap-2">
          <div className="flex items-center gap-2 rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5">
            <MagnifyingGlass size={15} className="text-[var(--color-fg-muted)]" />
            <input
              value={lookupValue}
              onChange={(e) => setLookupValue(e.target.value)}
              placeholder="输入学员 ID 查看档案"
              className="w-44 bg-transparent text-sm outline-none placeholder:text-[var(--color-fg-muted)]"
            />
          </div>
          <Button type="submit" size="sm" disabled={!lookupValue.trim()}>
            查看
          </Button>
        </form>
      </div>

      <Tabs defaultValue="insights">
        <TabsList className="mb-5">
          <TabsTrigger value="insights">教学洞察</TabsTrigger>
          <TabsTrigger value="metrics">北极星指标</TabsTrigger>
          <TabsTrigger value="review">候选题审核</TabsTrigger>
        </TabsList>

        <TabsContent value="insights">
          {loading ? (
            <DashboardSkeleton />
          ) : error ? (
            <Card>
              <CardContent className="pt-5">
                <div className="h-64">
                  <ErrorState message={error} onRetry={reload} />
                </div>
              </CardContent>
            </Card>
          ) : data && overview ? (
            <div className="flex flex-col gap-4">
              <OverviewBar {...overview} />
              <MasteryMatrix topics={data.topics} />
              <div className="grid gap-4 lg:grid-cols-2">
                <WeakRanking ranking={data.weak_ranking} />
                <MilestoneFunnel milestones={data.milestones} />
              </div>
              <LearnerList coursePackId={coursePackId} onSelect={setLearnerId} />
            </div>
          ) : null}
        </TabsContent>

        <TabsContent value="metrics">
          {metricsState.loading ? (
            <DashboardSkeleton />
          ) : metricsState.error ? (
            <Card>
              <CardContent className="pt-5">
                <div className="h-64">
                  <ErrorState message={metricsState.error} onRetry={metricsState.reload} />
                </div>
              </CardContent>
            </Card>
          ) : metricsState.metrics ? (
            <MetricsPanel metrics={metricsState.metrics} />
          ) : null}
        </TabsContent>

        <TabsContent value="review">
          <CandidateReview coursePackId={coursePackId} />
        </TabsContent>
      </Tabs>

      <LearnerDrawer
        learnerId={learnerId}
        coursePackId={coursePackId}
        onClose={() => setLearnerId(null)}
        onCorrected={reload}
      />
    </div>
  );
}
