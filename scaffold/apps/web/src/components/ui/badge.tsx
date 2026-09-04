import type { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

type BadgeTone = 'neutral' | 'accent' | 'known' | 'fuzzy' | 'unknown';

const toneClasses: Record<BadgeTone, string> = {
  neutral: 'bg-[var(--color-surface-2)] text-[var(--color-fg-muted)]',
  accent: 'bg-[var(--color-accent-soft)] text-[var(--color-accent)]',
  known: 'bg-[color-mix(in_srgb,var(--color-known)_15%,transparent)] text-[var(--color-known)]',
  fuzzy: 'bg-[color-mix(in_srgb,var(--color-fuzzy)_15%,transparent)] text-[var(--color-fuzzy)]',
  unknown:
    'bg-[color-mix(in_srgb,var(--color-unknown)_15%,transparent)] text-[var(--color-unknown)]',
};

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
}

export function Badge({ className, tone = 'neutral', ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
        toneClasses[tone],
        className,
      )}
      {...props}
    />
  );
}
