import { useEffect } from 'react';
import { animate, useMotionValue, useTransform, motion } from 'motion/react';
import { Users, Warning, Target, Flag } from '@phosphor-icons/react';
import type { Icon } from '@phosphor-icons/react';
import { Card } from '@/components/ui/card';

/** 数字滚动:用 useMotionValue 承载连续值,而非 useState(taste-skill)。 */
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
}: {
  icon: Icon;
  label: string;
  value: number;
  suffix?: string;
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
      </div>
    </Card>
  );
}

interface OverviewBarProps {
  learnerCount: number;
  weakCount: number;
  avgMastery: number;
  milestonePassRate: number;
}

export function OverviewBar({
  learnerCount,
  weakCount,
  avgMastery,
  milestonePassRate,
}: OverviewBarProps) {
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Metric icon={Users} label="学员数" value={learnerCount} />
      <Metric icon={Target} label="平均掌握度" value={avgMastery} suffix="%" />
      <Metric icon={Warning} label="薄弱知识点" value={weakCount} />
      <Metric icon={Flag} label="里程碑通过率" value={milestonePassRate} suffix="%" />
    </div>
  );
}
