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
import type { TopicInsight } from '@/api/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { axisTick, chartColors, tooltipStyle } from './chartTheme';

interface MasteryMatrixProps {
  topics: TopicInsight[];
}

export function MasteryMatrix({ topics }: MasteryMatrixProps) {
  const data = topics.map((t) => ({
    name: t.name,
    掌握: t.known,
    模糊: t.fuzzy,
    未掌握: t.unknown,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>知识点掌握度矩阵</CardTitle>
        <p className="text-xs text-[var(--color-fg-muted)]">各知识点上学员的掌握 / 模糊 / 未掌握人数</p>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="py-8 text-center text-sm text-[var(--color-fg-muted)]">暂无知识点数据</p>
        ) : (
          <ResponsiveContainer width="100%" height={Math.max(220, data.length * 44)}>
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
              <Bar dataKey="掌握" stackId="m" fill={chartColors.known} radius={[0, 0, 0, 0]} />
              <Bar dataKey="模糊" stackId="m" fill={chartColors.fuzzy} />
              <Bar dataKey="未掌握" stackId="m" fill={chartColors.unknown} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
