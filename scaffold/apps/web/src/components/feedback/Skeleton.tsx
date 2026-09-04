import { cn } from '@/lib/utils';

/** 骨架块:匹配最终布局的占位,禁用通用 spinner。 */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-[calc(var(--radius)-2px)] bg-[var(--color-surface-2)]',
        className,
      )}
    />
  );
}
