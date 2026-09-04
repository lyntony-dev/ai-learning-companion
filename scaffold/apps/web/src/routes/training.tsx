import { useState } from 'react';
import { Barbell, CheckCircle, XCircle, ArrowRight } from '@phosphor-icons/react';
import { DEFAULT_COURSE_PACK } from '@/api/training';
import { useTraining } from '@/hooks/useTraining';
import type { GradeResponse } from '@/api/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/feedback/Skeleton';
import { ErrorState } from '@/components/feedback/ErrorState';

const LEVEL_LABEL: Record<string, string> = {
  known: '已掌握',
  fuzzy: '模糊',
  unknown: '待巩固',
};
const LEVEL_TONE: Record<string, 'known' | 'fuzzy' | 'unknown'> = {
  known: 'known',
  fuzzy: 'fuzzy',
  unknown: 'unknown',
};
const DIFFICULTY_LABEL: Record<string, string> = {
  easy: '简单',
  medium: '中等',
  hard: '困难',
};
const DIFFICULTY_TONE: Record<string, 'known' | 'fuzzy' | 'unknown'> = {
  easy: 'known',
  medium: 'fuzzy',
  hard: 'unknown',
};

function scoreTone(score: number): 'known' | 'fuzzy' | 'unknown' {
  if (score >= 0.8) return 'known';
  if (score >= 0.4) return 'fuzzy';
  return 'unknown';
}

/** 批改结果卡:分数、逐维得分、反馈、掌握度变化。 */
function GradeResult({ grade }: { grade: GradeResponse }) {
  const pct = Math.round(grade.score * 100);
  const tone = scoreTone(grade.score);
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="flex items-center gap-2">
            {grade.passed ? (
              <CheckCircle size={18} weight="fill" className="text-[var(--color-known)]" />
            ) : (
              <XCircle size={18} weight="fill" className="text-[var(--color-fuzzy)]" />
            )}
            批改结果
          </CardTitle>
          <Badge tone={tone}>得分 {pct}</Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <p className="text-sm leading-relaxed text-[var(--color-fg)]">{grade.feedback}</p>

        <div className="flex flex-col gap-2">
          {grade.dimensions.map((d) => {
            const dpct = Math.round(d.score * 100);
            return (
              <div key={d.key} className="flex items-center gap-3">
                <span className="w-24 shrink-0 text-xs text-[var(--color-fg-muted)]">{d.name}</span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--color-surface-2)]">
                  <div
                    className="h-full rounded-full bg-[var(--color-accent)]"
                    style={{ width: `${dpct}%` }}
                  />
                </div>
                <span className="w-8 shrink-0 text-right text-xs tabular-nums text-[var(--color-fg-muted)]">
                  {dpct}
                </span>
              </div>
            );
          })}
        </div>

        <div className="flex items-center gap-2 border-t border-[var(--color-border)] pt-3 text-xs text-[var(--color-fg-muted)]">
          <span>知识点掌握度更新为</span>
          <Badge tone={LEVEL_TONE[grade.mastery.level] ?? 'neutral'}>
            {LEVEL_LABEL[grade.mastery.level] ?? grade.mastery.level}
          </Badge>
          {grade.mastery.overwritten ? <span>(已覆盖此前评估)</span> : null}
        </div>
      </CardContent>
    </Card>
  );
}

export function TrainingPage() {
  const coursePackId = DEFAULT_COURSE_PACK;
  const { question, grade, loading, grading, error, nextQuestion, submit } = useTraining(coursePackId);
  const [answer, setAnswer] = useState('');

  const started = loading || question !== null;

  const handleNext = () => {
    setAnswer('');
    nextQuestion();
  };

  const handleSubmit = () => {
    const text = answer.trim();
    if (!text || grading) return;
    submit(text);
  };

  return (
    <div className="mx-auto h-full max-w-2xl overflow-y-auto px-6 py-6">
      <div className="mb-5 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold">训练闭环</h1>
          <p className="text-sm text-[var(--color-fg-muted)]">
            针对薄弱知识点自适应出题 · 批改后更新掌握度
          </p>
        </div>
        {started ? (
          <Button variant="outline" size="sm" onClick={handleNext} disabled={loading || grading}>
            换一题
          </Button>
        ) : null}
      </div>

      {/* 未开始:引导卡 */}
      {!started && !error ? (
        <div className="flex h-[60vh] flex-col items-center justify-center gap-3 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-surface-2)] text-[var(--color-fg-muted)]">
            <Barbell size={24} weight="duotone" />
          </div>
          <h2 className="text-base font-semibold">开始一轮训练</h2>
          <p className="max-w-sm text-sm text-[var(--color-fg-muted)]">
            系统会挑选你最需要巩固的知识点出题。作答后由 AI 依课程评分维度批改,并更新你的掌握度。
          </p>
          <Button onClick={handleNext}>开始出题</Button>
        </div>
      ) : null}

      {/* 出题中 */}
      {loading ? (
        <div className="flex flex-col gap-4">
          <Skeleton className="h-28" />
          <Skeleton className="h-40" />
        </div>
      ) : null}

      {/* 出题失败 */}
      {error && !loading && !grading ? (
        <Card>
          <CardContent className="pt-5">
            <div className="h-52">
              <ErrorState message={error} onRetry={handleNext} />
            </div>
          </CardContent>
        </Card>
      ) : null}

      {/* 题目 + 作答 */}
      {question && !loading ? (
        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Badge tone="accent">{question.topic_name}</Badge>
                {question.difficulty ? (
                  <Badge tone={DIFFICULTY_TONE[question.difficulty] ?? 'neutral'}>
                    {DIFFICULTY_LABEL[question.difficulty] ?? question.difficulty}
                  </Badge>
                ) : null}
                <span className="text-xs text-[var(--color-fg-muted)]">
                  {question.source === 'preset' ? '预置题' : 'AI 生成题'}
                </span>
              </div>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-[var(--color-fg)]">
                {question.prompt}
              </p>
            </CardContent>
          </Card>

          {/* 作答:Enter 换行,点击按钮提交(防误触) */}
          <div className="rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface)] p-2">
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              rows={5}
              disabled={grading}
              placeholder="写下你的解答…(Enter 换行,点击下方按钮提交批改)"
              className="min-h-28 w-full resize-none bg-transparent px-2 py-1.5 text-sm outline-none placeholder:text-[var(--color-fg-muted)] disabled:opacity-60"
            />
            <div className="flex justify-end px-1 pb-1">
              <Button size="sm" onClick={handleSubmit} disabled={grading || !answer.trim()}>
                {grading ? '批改中…' : '提交批改'}
              </Button>
            </div>
          </div>

          {error && !grading ? (
            <div className="rounded-[var(--radius)] border border-[color-mix(in_srgb,var(--color-unknown)_40%,transparent)] bg-[color-mix(in_srgb,var(--color-unknown)_8%,transparent)] px-3 py-2 text-sm text-[var(--color-unknown)]">
              {error}
            </div>
          ) : null}

          {/* 批改中 */}
          {grading ? <Skeleton className="h-48" /> : null}

          {/* 批改结果 */}
          {grade && !grading ? (
            <>
              <GradeResult grade={grade} />
              <div className="flex justify-center">
                <Button variant="outline" onClick={handleNext}>
                  下一题
                  <ArrowRight size={15} />
                </Button>
              </div>
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
