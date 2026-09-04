import { useEffect, useState } from 'react';
import { fetchLearningArchive } from '@/api/archive';
import { ApiError } from '@/api/client';
import type { LearningArchiveResponse } from '@/api/types';

interface UseArchiveResult {
  archive: LearningArchiveResponse | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/**
 * 我的学习档案(Tier 2-6):加载本人本课程包的学习轨迹聚合。
 * 四态由消费方按 loading / error / (archive 空口径) / success 渲染。
 * 需登录;未登录时后端 401,以 error 呈现(页面已在路由层守卫跳登录)。
 */
export function useArchive(coursePackId: string): UseArchiveResult {
  const [archive, setArchive] = useState<LearningArchiveResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    fetchLearningArchive(coursePackId, controller.signal)
      .then((res) => setArchive(res))
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setError(err instanceof ApiError ? err.message : '学习档案加载失败。');
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [coursePackId, nonce]);

  return { archive, loading, error, reload: () => setNonce((n) => n + 1) };
}
