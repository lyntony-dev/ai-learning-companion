import { useCallback, useEffect, useState } from 'react';
import { listLearners } from '@/api/insights';
import { ApiError } from '@/api/client';
import type { LearnerListResponse } from '@/api/types';

interface UseLearnersResult {
  data: LearnerListResponse | null;
  loading: boolean;
  error: string | null;
  offset: number;
  setOffset: (offset: number) => void;
  reload: () => void;
}

const PAGE_SIZE = 20;

/**
 * 学员列表(讲师只读,分页)。需讲师身份;后端 require_teacher 未通过时以 error 呈现(401/403)。
 * 四态由消费方渲染。offset 变化即翻页。
 */
export function useLearners(coursePackId: string): UseLearnersResult {
  const [data, setData] = useState<LearnerListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [nonce, setNonce] = useState(0);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    listLearners(coursePackId, PAGE_SIZE, offset, controller.signal)
      .then((res) => setData(res))
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setError(err instanceof ApiError ? err.message : '学员列表加载失败。');
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [coursePackId, offset, nonce]);

  return { data, loading, error, offset, setOffset, reload };
}
