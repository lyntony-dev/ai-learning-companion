import { useCallback, useEffect, useState } from 'react';
import { getCourseInsights } from '@/api/insights';
import { ApiError } from '@/api/client';
import type { CourseInsightsResponse } from '@/api/types';

interface UseInsightsResult {
  data: CourseInsightsResponse | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

export function useInsights(coursePackId: string): UseInsightsResult {
  const [data, setData] = useState<CourseInsightsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    getCourseInsights(coursePackId, controller.signal)
      .then((res) => setData(res))
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setError(err instanceof ApiError ? err.message : '洞察数据加载失败。');
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [coursePackId, nonce]);

  return { data, loading, error, reload };
}
