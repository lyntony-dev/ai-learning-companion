import * as Dialog from '@radix-ui/react-dialog';
import { X } from '@phosphor-icons/react';
import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { getLearnerProfile, correctMastery } from '@/api/insights';
import { ApiError } from '@/api/client';
import { useAuth } from '@/lib/auth';
import type { LearnerProfileResponse, MasteryEntry, MasteryLevel } from '@/api/types';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/feedback/Skeleton';

interface LearnerDrawerProps {
  learnerId: string | null;
  coursePackId: string;
  onClose: () => void;
  onCorrected: () => void;
}

const LEVELS: { value: MasteryLevel; label: string; tone: 'known' | 'fuzzy' | 'unknown' }[] = [
  { value: 'known', label: '掌握', tone: 'known' },
  { value: 'fuzzy', label: '模糊', tone: 'fuzzy' },
  { value: 'unknown', label: '未掌握', tone: 'unknown' },
];

export function LearnerDrawer({ learnerId, coursePackId, onClose, onCorrected }: LearnerDrawerProps) {
  const { session } = useAuth();
  const instructor = session?.username ?? 'teacher';
  const open = learnerId !== null;
  const [profile, setProfile] = useState<LearnerProfileResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savingTopic, setSavingTopic] = useState<string | null>(null);

  useEffect(() => {
    if (!learnerId) return;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setProfile(null);
    getLearnerProfile(learnerId, coursePackId, controller.signal)
      .then(setProfile)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setError(err instanceof ApiError ? err.message : '档案加载失败。');
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [learnerId, coursePackId]);

  const handleCorrect = (entry: MasteryEntry, level: MasteryLevel) => {
    if (!learnerId || entry.level === level) return;
    // 乐观更新
    const prevLevel = entry.level;
    setSavingTopic(entry.topic_id);
    setProfile((p) =>
      p
        ? {
            ...p,
            masteries: p.masteries.map((m) =>
              m.topic_id === entry.topic_id
                ? { ...m, level, source: 'instructor_corrected', updated_by: instructor }
                : m,
            ),
          }
        : p,
    );
    correctMastery(
      { learner_id: learnerId, topic_id: entry.topic_id, level },
      coursePackId,
    )
      .then(() => onCorrected())
      .catch((err: unknown) => {
        // 回滚
        setProfile((p) =>
          p
            ? {
                ...p,
                masteries: p.masteries.map((m) =>
                  m.topic_id === entry.topic_id ? { ...m, level: prevLevel } : m,
                ),
              }
            : p,
        );
        setError(err instanceof ApiError ? err.message : '修正失败,请重试。');
      })
      .finally(() => setSavingTopic(null));
  };

  return (
    <Dialog.Root open={open} onOpenChange={(o) => !o && onClose()}>
      <AnimatePresence>
        {open ? (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild>
              <motion.div
                className="fixed inset-0 z-40 bg-black/30"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              />
            </Dialog.Overlay>
            <Dialog.Content asChild aria-describedby={undefined}>
              <motion.div
                className="fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col border-l border-[var(--color-border)] bg-[var(--color-bg)] shadow-xl"
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                transition={{ type: 'spring', stiffness: 320, damping: 34 }}
              >
                <div className="flex items-center justify-between border-b border-[var(--color-border)] p-4">
                  <div>
                    <Dialog.Title className="text-sm font-semibold">学员档案</Dialog.Title>
                    <p className="text-xs text-[var(--color-fg-muted)]">{learnerId}</p>
                  </div>
                  <Button variant="ghost" size="icon" onClick={onClose} aria-label="关闭">
                    <X size={18} />
                  </Button>
                </div>

                <div className="min-h-0 flex-1 overflow-y-auto p-4">
                  {loading ? (
                    <div className="flex flex-col gap-3">
                      {[0, 1, 2, 3].map((i) => (
                        <Skeleton key={i} className="h-16 w-full" />
                      ))}
                    </div>
                  ) : error ? (
                    <p className="text-sm text-[var(--color-unknown)]">{error}</p>
                  ) : profile && profile.masteries.length > 0 ? (
                    <div className="flex flex-col gap-3">
                      {profile.masteries.map((entry) => (
                        <div
                          key={entry.topic_id}
                          className="rounded-[var(--radius)] border border-[var(--color-border)] p-3"
                        >
                          <div className="mb-2 flex items-center justify-between gap-2">
                            <span className="truncate text-sm font-medium">{entry.name}</span>
                            {entry.source === 'instructor_corrected' ? (
                              <Badge tone="accent">讲师已修正</Badge>
                            ) : (
                              <Badge tone="neutral">系统推断</Badge>
                            )}
                          </div>
                          <div className="flex gap-1.5">
                            {LEVELS.map((lv) => {
                              const active = entry.level === lv.value;
                              return (
                                <button
                                  key={lv.value}
                                  type="button"
                                  disabled={savingTopic === entry.topic_id}
                                  onClick={() => handleCorrect(entry, lv.value)}
                                  className={
                                    'flex-1 rounded-[calc(var(--radius)-2px)] border px-2 py-1 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] disabled:opacity-50 ' +
                                    (active
                                      ? 'border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-accent)]'
                                      : 'border-[var(--color-border)] text-[var(--color-fg-muted)] hover:bg-[var(--color-surface-2)]')
                                  }
                                  aria-pressed={active}
                                >
                                  {lv.label}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-[var(--color-fg-muted)]">该学员暂无掌握度记录。</p>
                  )}
                </div>

                <div className="border-t border-[var(--color-border)] p-3">
                  <p className="text-center text-xs text-[var(--color-fg-muted)]">
                    点击掌握度按钮即写回,修正后来源标记为「讲师已修正」。
                  </p>
                </div>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        ) : null}
      </AnimatePresence>
    </Dialog.Root>
  );
}
