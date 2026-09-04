import { useState } from 'react';
import {
  Flag,
  CheckCircle,
  Circle,
  DotsThreeCircle,
  Trophy,
  BookOpen,
  ClipboardText,
  Lightbulb,
  Rocket,
  Stack,
  Compass,
} from '@phosphor-icons/react';
import { DEFAULT_COURSE_PACK } from '@/api/capstone';
import { useCapstone } from '@/hooks/useCapstone';
import type { ProjectMilestone } from '@/api/types';
import { ApiError } from '@/api/client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/feedback/Skeleton';
import { ErrorState } from '@/components/feedback/ErrorState';

const STATUS_LABEL: Record<string, string> = {
  not_started: '未开始',
  in_progress: '进行中',
  passed: '已达标',
};
const STATUS_TONE: Record<string, 'neutral' | 'fuzzy' | 'known'> = {
  not_started: 'neutral',
  in_progress: 'fuzzy',
  passed: 'known',
};

function StatusIcon({ status }: { status: string }) {
  if (status === 'passed')
    return <CheckCircle size={20} weight="fill" className="text-[var(--color-known)]" />;
  if (status === 'in_progress')
    return <DotsThreeCircle size={20} weight="fill" className="text-[var(--color-fuzzy)]" />;
  return <Circle size={20} className="text-[var(--color-fg-muted)]" />;
}

/** 项目说明书:立项前 / 立项后都展示,让学生看懂"这是什么项目、要做出什么"。 */
function ProjectBrief({
  overview,
  background,
  finalDeliverable,
}: {
  overview: string;
  background: string;
  finalDeliverable: string;
}) {
  if (!overview && !background && !finalDeliverable) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BookOpen size={18} weight="duotone" className="text-[var(--color-accent)]" />
          项目说明书
        </CardTitle>
        <p className="text-xs text-[var(--color-fg-muted)]">
          结课项目的总体要求:你要做什么、为什么、最终交付什么。
        </p>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {overview ? (
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--color-fg-muted)]">
              项目目标
            </p>
            <p className="whitespace-pre-line text-sm text-[var(--color-fg)]">{overview}</p>
          </div>
        ) : null}
        {background ? (
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--color-fg-muted)]">
              背景 / 场景
            </p>
            <p className="whitespace-pre-line text-sm text-[var(--color-fg)]">{background}</p>
          </div>
        ) : null}
        {finalDeliverable ? (
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--color-fg-muted)]">
              最终交付物
            </p>
            <p className="whitespace-pre-line text-sm text-[var(--color-fg)]">{finalDeliverable}</p>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

/** 立项向导:多字段引导(想做什么 Agent / 面向谁 / 预期难点),点击按钮提交生成个性化计划。 */
function KickoffWizard({
  creating,
  onCreate,
}: {
  creating: boolean;
  onCreate: (args: { goal: string; audience: string; difficulty: string }) => Promise<void>;
}) {
  const [goal, setGoal] = useState('');
  const [audience, setAudience] = useState('');
  const [difficulty, setDifficulty] = useState('');
  const [err, setErr] = useState<string | null>(null);

  const canSubmit = goal.trim().length > 0 && !creating;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setErr(null);
    try {
      await onCreate({ goal: goal.trim(), audience: audience.trim(), difficulty: difficulty.trim() });
    } catch (e: unknown) {
      setErr(e instanceof ApiError ? e.message : '立项失败,请重试。');
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Rocket size={18} weight="duotone" className="text-[var(--color-accent)]" />
          立项向导
        </CardTitle>
        <p className="text-xs text-[var(--color-fg-muted)]">
          说说你想做的 Agent,系统会结合课程内容,把它收敛成一个清晰的项目,并为每个里程碑生成
          「针对你这个项目的可勾选清单」——你只要照着勾选推进即可。
        </p>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div>
          <label className="mb-1.5 block text-xs font-semibold text-[var(--color-fg)]">
            想做一个什么 Agent?<span className="text-[var(--color-accent)]"> *</span>
          </label>
          <div className="rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface)] p-2">
            <textarea
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              rows={3}
              disabled={creating}
              placeholder="例如:一个能回答我课程笔记问题、必要时查时间/算数的个人学习助手…(Enter 换行,点下方按钮提交)"
              className="min-h-16 w-full resize-none bg-transparent px-2 py-1.5 text-sm outline-none placeholder:text-[var(--color-fg-muted)] disabled:opacity-60"
            />
          </div>
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-semibold text-[var(--color-fg)]">
            面向谁 / 什么场景?
          </label>
          <div className="rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface)] p-2">
            <textarea
              value={audience}
              onChange={(e) => setAudience(e.target.value)}
              rows={2}
              disabled={creating}
              placeholder="例如:面向像我一样笔记很多但搜不准的开发者"
              className="min-h-10 w-full resize-none bg-transparent px-2 py-1.5 text-sm outline-none placeholder:text-[var(--color-fg-muted)] disabled:opacity-60"
            />
          </div>
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-semibold text-[var(--color-fg)]">
            预期难点 / 想挑战什么?<span className="text-[var(--color-fg-muted)]">(选填)</span>
          </label>
          <div className="rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface)] p-2">
            <textarea
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
              rows={2}
              disabled={creating}
              placeholder="例如:担心检索召回不准,想试试多轮对话记忆"
              className="min-h-10 w-full resize-none bg-transparent px-2 py-1.5 text-sm outline-none placeholder:text-[var(--color-fg-muted)] disabled:opacity-60"
            />
          </div>
        </div>

        {err ? (
          <div className="rounded-[var(--radius)] border border-[color-mix(in_srgb,var(--color-unknown)_40%,transparent)] bg-[color-mix(in_srgb,var(--color-unknown)_8%,transparent)] px-3 py-2 text-sm text-[var(--color-unknown)]">
            {err}
          </div>
        ) : null}

        {creating ? (
          <div className="flex flex-col gap-2">
            <p className="text-xs text-[var(--color-fg-muted)]">正在为你的项目生成里程碑清单…</p>
            <Skeleton className="h-24" />
          </div>
        ) : (
          <div className="flex justify-end">
            <Button onClick={handleSubmit} disabled={!canSubmit}>
              生成我的项目计划
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/** 里程碑卡:名称 + 状态 + 个性化清单(可勾选)。 */
function MilestoneCard({
  milestone,
  index,
  isCurrent,
  disabled,
  onToggle,
}: {
  milestone: ProjectMilestone;
  index: number;
  isCurrent: boolean;
  disabled: boolean;
  onToggle: (itemId: string, checked: boolean) => void;
}) {
  return (
    <Card
      className={
        isCurrent ? 'border-[var(--color-accent)]' : undefined
      }
    >
      <CardHeader>
        <div className="flex items-center gap-3">
          <StatusIcon status={milestone.status} />
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--color-surface-2)] text-xs text-[var(--color-fg-muted)]">
            {index + 1}
          </span>
          <CardTitle className="flex-1">{milestone.name}</CardTitle>
          {isCurrent ? <Badge tone="accent">当前</Badge> : null}
          <Badge tone={STATUS_TONE[milestone.status] ?? 'neutral'}>
            {STATUS_LABEL[milestone.status] ?? milestone.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {milestone.deliverable ? (
          <div className="flex gap-2.5 rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface-2)] p-3">
            <ClipboardText
              size={18}
              weight="duotone"
              className="mt-0.5 shrink-0 text-[var(--color-accent)]"
            />
            <div>
              <p className="mb-0.5 text-xs font-semibold text-[var(--color-fg)]">交付要求</p>
              <p className="whitespace-pre-line text-sm text-[var(--color-fg-muted)]">
                {milestone.deliverable}
              </p>
            </div>
          </div>
        ) : null}

        {/* 个性化清单:绑定到学生自己的项目 */}
        <div className="flex flex-col gap-1.5">
          {milestone.items.map((it) => (
            <label
              key={it.id}
              className="flex cursor-pointer items-start gap-2.5 rounded-[var(--radius)] px-2 py-1.5 hover:bg-[var(--color-surface-2)]"
            >
              <input
                type="checkbox"
                checked={it.checked}
                disabled={disabled}
                onChange={(e) => onToggle(it.id, e.target.checked)}
                className="mt-0.5 h-4 w-4 shrink-0 accent-[var(--color-accent)]"
              />
              <span
                className={`text-sm ${
                  it.checked
                    ? 'text-[var(--color-fg-muted)] line-through'
                    : 'text-[var(--color-fg)]'
                }`}
              >
                {it.text}
              </span>
            </label>
          ))}
        </div>

        {milestone.hint ? (
          <div className="flex items-start gap-2 px-1 text-xs text-[var(--color-fg-muted)]">
            <Lightbulb size={15} weight="duotone" className="mt-0.5 shrink-0 text-[var(--color-fuzzy)]" />
            <span className="whitespace-pre-line">提示:{milestone.hint}</span>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function CapstonePage() {
  const coursePackId = DEFAULT_COURSE_PACK;
  const { data, loading, error, reload, create, creating, toggle } = useCapstone(coursePackId);
  const [toggleError, setToggleError] = useState<string | null>(null);

  const handleToggle = async (itemId: string, checked: boolean) => {
    setToggleError(null);
    try {
      await toggle(itemId, checked);
    } catch (e: unknown) {
      setToggleError(e instanceof ApiError ? e.message : '更新清单失败,请重试。');
    }
  };

  return (
    <div className="mx-auto h-full max-w-3xl overflow-y-auto px-6 py-6">
      <div className="mb-5">
        <h1 className="text-lg font-semibold">项目陪练</h1>
        <p className="text-sm text-[var(--color-fg-muted)]">
          立项你的结课项目,拿到一份专属清单,逐项勾选推进到交付
        </p>
      </div>

      {loading ? (
        <div className="flex flex-col gap-4">
          <Skeleton className="h-16" />
          <Skeleton className="h-56" />
          <Skeleton className="h-40" />
        </div>
      ) : error ? (
        <Card>
          <CardContent className="pt-5">
            <div className="h-56">
              <ErrorState message={error} onRetry={reload} />
            </div>
          </CardContent>
        </Card>
      ) : data ? (
        <div className="flex flex-col gap-4">
          {!data.has_project ? (
            /* ===== 未立项:项目说明书 + 立项向导 ===== */
            <>
              <ProjectBrief
                overview={data.overview}
                background={data.background}
                finalDeliverable={data.final_deliverable}
              />
              <KickoffWizard creating={creating} onCreate={create} />
            </>
          ) : (
            /* ===== 已立项:进度总览 + 项目卡 + 个性化清单 ===== */
            <>
              {/* 进度总览 */}
              <Card>
                <CardContent className="flex items-center gap-4 pt-5">
                  <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)]">
                    {data.all_passed ? (
                      <Trophy size={22} weight="fill" />
                    ) : (
                      <Flag size={22} weight="duotone" />
                    )}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-semibold">{data.capstone_name}</p>
                    <p className="text-xs text-[var(--color-fg-muted)]">
                      {data.all_passed
                        ? '恭喜,全部里程碑已完成!'
                        : `已完成 ${data.passed_count} / ${data.total} 个里程碑`}
                    </p>
                  </div>
                  <div className="h-2 w-28 overflow-hidden rounded-full bg-[var(--color-surface-2)]">
                    <div
                      className="h-full rounded-full bg-[var(--color-known)]"
                      style={{
                        width: `${data.total ? (data.passed_count / data.total) * 100 : 0}%`,
                      }}
                    />
                  </div>
                </CardContent>
              </Card>

              {/* 项目卡:立项收敛后的成果 */}
              {data.card ? (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Compass size={18} weight="duotone" className="text-[var(--color-accent)]" />
                      我的项目
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-3">
                    <div>
                      <p className="text-sm font-semibold text-[var(--color-fg)]">
                        {data.card.title}
                      </p>
                      {data.card.scope ? (
                        <p className="mt-1 whitespace-pre-line text-sm text-[var(--color-fg-muted)]">
                          {data.card.scope}
                        </p>
                      ) : null}
                    </div>
                    {data.card.tech_stack.length ? (
                      <div className="flex flex-col gap-1.5">
                        <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--color-fg-muted)]">
                          <Stack size={14} weight="duotone" />
                          推荐技术选型
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {data.card.tech_stack.map((t) => (
                            <Badge key={t} tone="accent">
                              {t}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </CardContent>
                </Card>
              ) : null}

              {toggleError ? (
                <div className="rounded-[var(--radius)] border border-[color-mix(in_srgb,var(--color-unknown)_40%,transparent)] bg-[color-mix(in_srgb,var(--color-unknown)_8%,transparent)] px-3 py-2 text-sm text-[var(--color-unknown)]">
                  {toggleError}
                </div>
              ) : null}

              {/* 里程碑 + 个性化清单 */}
              {data.milestones.map((m, i) => (
                <MilestoneCard
                  key={m.milestone_id}
                  milestone={m}
                  index={i}
                  isCurrent={m.milestone_id === data.current_milestone_id}
                  disabled={false}
                  onToggle={handleToggle}
                />
              ))}
            </>
          )}
        </div>
      ) : null}
    </div>
  );
}
