/** 图表配色/样式:统一取设计 token,覆写 Recharts 默认(taste-skill)。 */
export const chartColors = {
  known: 'var(--color-known)',
  fuzzy: 'var(--color-fuzzy)',
  unknown: 'var(--color-unknown)',
  accent: 'var(--color-accent)',
  grid: 'var(--color-border)',
  axis: 'var(--color-fg-muted)',
  passed: 'var(--color-known)',
  inProgress: 'var(--color-fuzzy)',
  notStarted: 'var(--color-border)',
};

export const axisTick = { fill: 'var(--color-fg-muted)', fontSize: 12 };

export const tooltipStyle = {
  backgroundColor: 'var(--color-bg)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius)',
  fontSize: 12,
  color: 'var(--color-fg)',
} as const;
