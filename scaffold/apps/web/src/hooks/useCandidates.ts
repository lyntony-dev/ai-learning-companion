import { useCallback, useEffect, useState } from 'react';
import { approveCandidate, fetchCandidates, rejectCandidate } from '@/api/training';
import { ApiError } from '@/api/client';
import type { CandidateQuestion } from '@/api/types';

interface UseCandidatesResult {
  candidates: CandidateQuestion[];
  loading: boolean;
  error: string | null;
  reload: () => void;
  /** 正在处理(审核/驳回)的 question_id,用于禁用按钮 */
  pendingId: string | null;
  actionError: string | null;
  approve: (questionId: string) => Promise<void>;
  reject: (questionId: string) => Promise<void>;
}

/**
 * 讲师审核候选题(ADR-0006 飞轮)。通过/驳回后本地摘除该条,失败保留并报错。
 * 需讲师身份;后端 require_teacher 未通过时以 error 呈现(401/403)。
 */
export function useCandidates(coursePackId: string): UseCandidatesResult {
  const [candidates, setCandidates] = useState<CandidateQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    fetchCandidates(coursePackId, controller.signal)
      .then((res) => setCandidates(res.candidates))
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setError(err instanceof ApiError ? err.message : '候选题加载失败。');
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [coursePackId, nonce]);

  const runAction = useCallback(
    async (questionId: string, fn: () => Promise<unknown>) => {
      setPendingId(questionId);
      setActionError(null);
      try {
        await fn();
        setCandidates((prev) => prev.filter((c) => c.question_id !== questionId));
      } catch (err: unknown) {
        setActionError(err instanceof ApiError ? err.message : '操作失败,请重试。');
      } finally {
        setPendingId(null);
      }
    },
    [],
  );

  const approve = useCallback(
    (questionId: string) => runAction(questionId, () => approveCandidate(questionId, coursePackId)),
    [coursePackId, runAction],
  );
  const reject = useCallback(
    (questionId: string) => runAction(questionId, () => rejectCandidate(questionId, coursePackId)),
    [coursePackId, runAction],
  );

  return { candidates, loading, error, reload, pendingId, actionError, approve, reject };
}
