import type { Icon } from '@phosphor-icons/react';
import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon: Icon;
  title: string;
  description: string;
  badge?: string;
  children?: ReactNode;
}

export function EmptyState({ icon: IconCmp, title, description, badge, children }: EmptyStateProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-surface-2)] text-[var(--color-fg-muted)]">
        <IconCmp size={24} weight="duotone" />
      </div>
      <div className="flex items-center gap-2">
        <h2 className="text-base font-semibold">{title}</h2>
        {badge ? (
          <span className="rounded-full bg-[var(--color-accent-soft)] px-2 py-0.5 text-xs font-medium text-[var(--color-accent)]">
            {badge}
          </span>
        ) : null}
      </div>
      <p className="max-w-sm text-sm text-[var(--color-fg-muted)]">{description}</p>
      {children}
    </div>
  );
}
