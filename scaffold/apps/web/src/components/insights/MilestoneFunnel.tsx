import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { MilestoneInsight } from '@/api/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { axisTick, chartColors, tooltipStyle } from './chartTheme';

interface MilestoneFunnelProps {
  milestones: MilestoneInsight[];
}

export function MilestoneFunnel({ milestones }: MilestoneFunnelProps) {
  const data = milestones.map((m) => ({
    name: m.milestone,
    已通过: m.passed,
    进行中: m.in_progress,
    未开始: m.not_started,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>里程碑漏斗</CardTitle>
        <p className="text-xs text-[var(--color-fg-muted)]">各结课项目里程碑的学员进度分布</p>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="py-8 text-center text-sm text-[var(--color-fg-muted)]">暂无里程碑数据</p>
        ) : (
          <ResponsiveContainer width="100%" height={Math.max(200, data.length * 48)}>
            <BarChart data={data} layout="vertical" margin={{ left: 12, right: 12 }}>
              <CartesianGrid horizontal={false} stroke={chartColors.grid} />
              <XAxis type="number" tick={axisTick} axisLine={false} tickLine={false} />
              <YAxis
                type="category"
                dataKey="name"
                width={120}
                tick={axisTick}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip contentStyle={tooltipStyle} cursor={{ fill: 'var(--color-surface-2)' }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="已通过" stackId="s" fill={chartColors.passed} radius={[0, 0, 0, 0]} />
              <Bar dataKey="进行中" stackId="s" fill={chartColors.inProgress} />
              <Bar dataKey="未开始" stackId="s" fill={chartColors.notStarted} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
