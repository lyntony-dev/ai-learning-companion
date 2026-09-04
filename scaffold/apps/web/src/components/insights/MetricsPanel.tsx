import { useEffect } from 'react';
import { animate, useMotionValue, useTransform, motion } from 'motion/react';
import {
  ChatCircleDots,
  ShieldCheck,
  Target,
  Barbell,
  Trophy,
  Users,
} from '@phosphor-icons/react';
import type { Icon } from '@phosphor-icons/react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { NorthStarMetricsResponse } from '@/api/types';

/** 数字滚动:连续值用 useMotionValue 承载(与 OverviewBar 一致纪律)。 */
function AnimatedNumber({ value, suffix = '' }: { value: number; suffix?: string }) {
  const mv = useMotionValue(0);
  const rounded = useTransform(mv, (v) => `${Math.round(v)}${suffix}`);
  useEffect(() => {
    const controls = animate(mv, value, { duration: 0.8, ease: 'easeOut' });
    return () => controls.stop();
  }, [mv, value]);
  return <motion.span>{rounded}</motion.span>;
}

function Metric({
  icon: IconCmp,
  label,
  value,
  suffix,
  hint,
}: {
  icon: Icon;
  label: string;
  value: number;
  suffix?: string;
  hint?: string;
}) {
  return (
    <Card className="flex items-center gap-3 p-4">
      <div className="flex h-9 w-9 items-center justify-center rounded-[var(--radius)] bg-[var(--color-accent-soft)] text-[var(--color-accent)]">
        <IconCmp size={18} weight="duotone" />
      </div>
      <div>
        <div className="text-xl font-semibold tabular-nums">
          <AnimatedNumber value={value} suffix={suffix} />
        </div>
        <div className="text-xs text-[var(--color-fg-muted)]">{label}</div>
        {hint ? <div className="text-xs text-[var(--color-fg-muted)]">{hint}</div> : null}
      </div>
    </Card>
  );
}

/**
 * 北极星指标面板(Tier 3-7):把产品价值量化为可追踪的健康度。
 * 全部取自后端业务库真实聚合,无数据即为 0(不臆造)。
 */
export function MetricsPanel({ metrics }: { metrics: NorthStarMetricsResponse }) {
  const { engagement, honesty, mastery_progress, practice_quality, capstone_funnel } = metrics;
  const refusalPct = Math.round(honesty.refusal_rate * 100);
  const knownPct = Math.round(mastery_progress.known_rate * 100);
  const completionPct = Math.round(capstone_funnel.completion_rate * 100);

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
        <Metric icon={Users} label="活跃学员" value={engagement.active_learners} />
        <Metric icon={ChatCircleDots} label="问答轮次" value={engagement.qa_turns} />
        <Metric icon={Barbell} label="练习次数" value={engagement.practice_attempts} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck size={18} weight="duotone" className="text-[var(--color-accent)]" />
            诚实度(证据不足即拒答)
          </CardTitle>
          <p className="text-xs text-[var(--color-fg-muted)]">
            拒答是产品特性而非失败:材料不足时坦诚说明,不编造引用。
          </p>
        </CardHeader>
        <CardContent className="flex flex-wrap items-baseline gap-6">
          <div>
            <div className="text-2xl font-semibold tabular-nums">
              <AnimatedNumber value={refusalPct} suffix="%" />
            </div>
            <div className="text-xs text-[var(--color-fg-muted)]">拒答率</div>
          </div>
          <div className="text-sm text-[var(--color-fg-muted)]">
            {honesty.refused} / {honesty.qa_turns} 轮拒答
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <Metric
          icon={Target}
          label="已掌握占比"
          value={knownPct}
          suffix="%"
          hint={`${mastery_progress.known}/${mastery_progress.topics_tracked} 知识点`}
        />
        <Metric
          icon={Barbell}
          label="练习平均分"
          value={Math.round((practice_quality.avg_score ?? 0) * 100)}
          hint={practice_quality.avg_score === null ? '暂无练习' : `共 ${practice_quality.attempts} 次`}
        />
        <Metric
          icon={Trophy}
          label="结课率"
          value={completionPct}
          suffix="%"
          hint={`${capstone_funnel.completed}/${capstone_funnel.kickoff} 立项结课`}
        />
      </div>
    </div>
  );
}
