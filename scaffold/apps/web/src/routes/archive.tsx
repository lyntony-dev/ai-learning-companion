import { Navigate } from 'react-router-dom';
import { ChartLineUp, Books, Barbell, Trophy } from '@phosphor-icons/react';
import { useArchive } from '@/hooks/useArchive';
import { DEFAULT_COURSE_PACK } from '@/api/archive';
import { useAuth } from '@/lib/auth';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/feedback/Skeleton';
import { ErrorState } from '@/components/feedback/ErrorState';
import { EmptyState } from '@/components/feedback/EmptyState';
import type { LearningArchiveResponse } from '@/api/types';

const LEVEL_LABEL: Record<string, string> = {
  known: '已掌握',
  fuzzy: '模糊',
  unknown: '待巩固',
};
const LEVEL_TONE: Record<string, 'known' | 'fuzzy' | 'unknown'> = {
  known: 'known',
  fuzzy: 'fuzzy',
  unknown: 'unknown',
};
const SOURCE_LABEL: Record<string, string> = {
  system_inferred: '系统推断',
  instructor_corrected: '讲师订正',
};
const MILESTONE_LABEL: Record<string, string> = {
  not_started: '未开始',
  in_progress: '进行中',
  passed: '已通过',
};

/**
 * 我的学习档案(Tier 2-6):登录学生自查掌握度 / 练习 / 项目进度。
 * 数据只读本人(后端按 token 解析 learner_id),四态齐备。
 */
export function ArchivePage() {
  const { isAuthed } = useAuth();
  const { archive, loading, error, reload } = useArchive(DEFAULT_COURSE_PACK);

  if (!isAuthed) return <Navigate to="/login" replace />;

  return (
    <div className="mx-auto h-full max-w-3xl overflow-y-auto px-6 py-6">
      <div className="mb-5 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--color-surface-2)] text-[var(--color-accent)]">
          <ChartLineUp size={22} weight="duotone" />
        </div>
        <div>
          <h1 className="text-lg font-semibold">我的学习档案</h1>
          <p className="text-sm text-[var(--color-fg-muted)]">掌握度 · 练习记录 · 结课项目进度</p>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col gap-4">
          <Skeleton className="h-32" />
          <Skeleton className="h-48" />
          <Skeleton className="h-40" />
        </div>
      ) : null}

      {error && !loading ? (
        <Card>
          <CardContent className="pt-5">
            <div className="h-52">
              <ErrorState message={error} onRetry={reload} />
            </div>
          </CardContent>
        </Card>
      ) : null}

      {archive && !loading && !error ? <ArchiveBody archive={archive} /> : null}
    </div>
  );
}

function ArchiveBody({ archive }: { archive: LearningArchiveResponse }) {
  const { levels, topics_tracked, masteries, practice, capstone } = archive;
  const hasAnyData =
    topics_tracked > 0 || practice.attempts > 0 || capstone.has_project;

  if (!hasAnyData) {
    return (
      <div className="h-72">
        <EmptyState
          icon={Books}
          title="还没有学习记录"
          description="去训练闭环做几道题,或在项目陪练里立项,这里会汇总你的掌握度与进度。"
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* 掌握度分布 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Books size={18} weight="duotone" className="text-[var(--color-accent)]" />
            掌握度分布
          </CardTitle>
          <p className="text-xs text-[var(--color-fg-muted)]">
            覆盖 {topics_tracked} 个知识点
          </p>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-wrap gap-2">
            <Badge tone="known">已掌握 {levels.known}</Badge>
            <Badge tone="fuzzy">模糊 {levels.fuzzy}</Badge>
            <Badge tone="unknown">待巩固 {levels.unknown}</Badge>
          </div>
          {masteries.length > 0 ? (
            <ul className="flex flex-col divide-y divide-[var(--color-border)]">
              {masteries.map((m) => (
                <li key={m.topic_id} className="flex items-center justify-between gap-3 py-2">
                  <span className="text-sm text-[var(--color-fg)]">{m.name}</span>
                  <div className="flex items-center gap-2">
                    {m.source === 'instructor_corrected' ? (
                      <span className="text-xs text-[var(--color-fg-muted)]">
                        {SOURCE_LABEL[m.source] ?? m.source}
                      </span>
                    ) : null}
                    <Badge tone={LEVEL_TONE[m.level] ?? 'neutral'}>
                      {LEVEL_LABEL[m.level] ?? m.level}
                    </Badge>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-[var(--color-fg-muted)]">暂无已跟踪的知识点。</p>
          )}
        </CardContent>
      </Card>

      {/* 练习记录 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Barbell size={18} weight="duotone" className="text-[var(--color-accent)]" />
            练习记录
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-wrap gap-2">
            <Badge tone="neutral">累计作答 {practice.attempts}</Badge>
            <Badge tone="accent">
              平均分 {practice.avg_score === null ? '暂无' : `${Math.round(practice.avg_score * 100)} 分`}
            </Badge>
          </div>
          {practice.recent.length > 0 ? (
            <ul className="flex flex-col divide-y divide-[var(--color-border)]">
              {practice.recent.map((a, idx) => (
                <li
                  key={`${a.topic_id}-${a.created_at}-${idx}`}
                  className="flex items-center justify-between gap-3 py-2"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm text-[var(--color-fg)]">{a.name}</p>
                    <p className="text-xs text-[var(--color-fg-muted)]">{a.created_at}</p>
                  </div>
                  <Badge tone={a.score >= 0.8 ? 'known' : a.score >= 0.4 ? 'fuzzy' : 'unknown'}>
                    {Math.round(a.score * 100)} 分
                  </Badge>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-[var(--color-fg-muted)]">还没有练习记录。</p>
          )}
        </CardContent>
      </Card>

      {/* 结课项目进度 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Trophy size={18} weight="duotone" className="text-[var(--color-accent)]" />
            结课项目进度
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {capstone.has_project ? (
            <>
              {capstone.goal ? (
                <p className="text-sm text-[var(--color-fg)]">目标:{capstone.goal}</p>
              ) : null}
              <div className="flex flex-wrap gap-2">
                <Badge tone="accent">
                  里程碑 {capstone.passed}/{capstone.total} 通过
                </Badge>
              </div>
              {capstone.milestones.length > 0 ? (
                <ul className="flex flex-wrap gap-2">
                  {capstone.milestones.map((ms) => (
                    <li key={ms.milestone_id}>
                      <Badge tone={ms.status === 'passed' ? 'known' : 'neutral'}>
                        {MILESTONE_LABEL[ms.status] ?? ms.status}
                      </Badge>
                    </li>
                  ))}
                </ul>
              ) : null}
            </>
          ) : (
            <p className="text-sm text-[var(--color-fg-muted)]">
              还没有立项。去项目陪练开启你的结课项目。
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
