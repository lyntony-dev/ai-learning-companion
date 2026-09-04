import { Warning } from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[color-mix(in_srgb,var(--color-unknown)_12%,transparent)] text-[var(--color-unknown)]">
        <Warning size={24} weight="duotone" />
      </div>
      <p className="max-w-sm text-sm text-[var(--color-fg-muted)]">{message}</p>
      {onRetry ? (
        <Button variant="outline" size="sm" onClick={onRetry}>
          重试
        </Button>
      ) : null}
    </div>
  );
}
