import { useCallback, useRef, useState } from 'react';
import { fetchQuestion, gradeAnswer } from '@/api/training';
import { ApiError } from '@/api/client';
import type { GradeResponse, TrainingQuestion } from '@/api/types';
import { useAuth } from '@/lib/auth';

interface UseTrainingResult {
  question: TrainingQuestion | null;
  grade: GradeResponse | null;
  /** 出题请求进行中 */
  loading: boolean;
  /** 批改请求进行中 */
  grading: boolean;
  error: string | null;
  /** 取下一题(清空当前批改结果) */
  nextQuestion: () => void;
  /** 提交作答批改 */
  submit: (answer: string) => void;
}

/**
 * 训练一轮:出题 → 作答 → 批改。批改由服务端按 question_id 重载题目打分,
 * 前端不持有参考答案。同步等待(约十几秒),用 loading/grading 区分两个阶段。
 */
export function useTraining(coursePackId: string): UseTrainingResult {
  const { learnerId } = useAuth();
  const [question, setQuestion] = useState<TrainingQuestion | null>(null);
  const [grade, setGrade] = useState<GradeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [grading, setGrading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // 本轮已展示过的题目 id:「换一题」回传给后端以跳过,真正换到没做过的题。
  const seenIds = useRef<string[]>([]);

  const nextQuestion = useCallback(() => {
    setLoading(true);
    setError(null);
    setGrade(null);
    setQuestion(null);
    fetchQuestion({ learner_id: learnerId, exclude_ids: seenIds.current }, coursePackId)
      .then((res) => {
        if (res.question_id) {
          // 记录已见题;题池耗尽后后端会复用旧题,此时重置避免永远排除。
          if (seenIds.current.includes(res.question_id)) {
            seenIds.current = [res.question_id];
          } else {
            seenIds.current = [...seenIds.current, res.question_id];
          }
        }
        setQuestion(res);
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : '出题失败,请重试。');
      })
      .finally(() => setLoading(false));
  }, [coursePackId, learnerId]);

  const submit = useCallback(
    (answer: string) => {
      if (!question || !question.question_id) return;
      setGrading(true);
      setError(null);
      gradeAnswer(
        { learner_id: learnerId, question_id: question.question_id, answer },
        coursePackId,
      )
        .then((res) => setGrade(res))
        .catch((err: unknown) => {
          setError(err instanceof ApiError ? err.message : '批改失败,请重试。');
        })
        .finally(() => setGrading(false));
    },
    [question, coursePackId, learnerId],
  );

  return { question, grade, loading, grading, error, nextQuestion, submit };
}
