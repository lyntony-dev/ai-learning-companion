import { useEffect, useState } from 'react';
import { getNorthStarMetrics } from '@/api/insights';
import { ApiError } from '@/api/client';
import type { NorthStarMetricsResponse } from '@/api/types';

interface UseMetricsResult {
  metrics: NorthStarMetricsResponse | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/**
 * 北极星指标(Tier 3-7):讲师视角的课程健康度聚合。
 * 需讲师身份;后端 require_teacher 未通过时以 error 呈现(401/403)。四态由消费方渲染。
 */
export function useMetrics(coursePackId: string): UseMetricsResult {
  const [metrics, setMetrics] = useState<NorthStarMetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    getNorthStarMetrics(coursePackId, controller.signal)
      .then((res) => setMetrics(res))
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setError(err instanceof ApiError ? err.message : '指标加载失败。');
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [coursePackId, nonce]);

  return { metrics, loading, error, reload: () => setNonce((n) => n + 1) };
}
