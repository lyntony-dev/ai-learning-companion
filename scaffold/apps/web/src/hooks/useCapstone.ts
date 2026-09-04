import { useCallback, useEffect, useState } from 'react';
import { createProject, getProject, toggleItem } from '@/api/capstone';
import { ApiError } from '@/api/client';
import { useAuth } from '@/lib/auth';
import type { CapstoneProjectResponse } from '@/api/types';

interface CreateArgs {
  goal: string;
  audience: string;
  difficulty: string;
}

interface UseCapstoneResult {
  data: CapstoneProjectResponse | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
  /** 立项:提交想法生成项目卡 + 个性化清单;成功后刷新 */
  create: (args: CreateArgs) => Promise<void>;
  creating: boolean;
  /** 勾选/取消一条清单项(乐观更新,失败回滚) */
  toggle: (itemId: string, checked: boolean) => Promise<void>;
}

/**
 * 结课项目:立项向导 + 个性化清单。
 *  - 未立项:has_project=false,页面展示立项向导;
 *  - 已立项:展示项目卡与每里程碑可勾选清单,勾选推进里程碑状态。
 */
export function useCapstone(coursePackId: string): UseCapstoneResult {
  const { learnerId } = useAuth();
  const [data, setData] = useState<CapstoneProjectResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [nonce, setNonce] = useState(0);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    getProject(learnerId, coursePackId, controller.signal)
      .then((res) => setData(res))
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setError(err instanceof ApiError ? err.message : '项目状态加载失败。');
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [coursePackId, nonce, learnerId]);

  const create = useCallback(
    async ({ goal, audience, difficulty }: CreateArgs): Promise<void> => {
      setCreating(true);
      try {
        const res = await createProject(
          { learner_id: learnerId, goal, audience, difficulty },
          coursePackId,
        );
        setData(res);
      } finally {
        setCreating(false);
      }
    },
    [coursePackId, learnerId],
  );

  const toggle = useCallback(
    async (itemId: string, checked: boolean): Promise<void> => {
      // 乐观更新:先本地翻转,失败再回滚
      const prev = data;
      if (prev) {
        setData({
          ...prev,
          milestones: prev.milestones.map((m) => ({
            ...m,
            items: m.items.map((it) => (it.id === itemId ? { ...it, checked } : it)),
          })),
        });
      }
      try {
        const res = await toggleItem(itemId, { learner_id: learnerId, checked }, coursePackId);
        setData(res);
      } catch (err) {
        if (prev) setData(prev);
        throw err;
      }
    },
    [coursePackId, data, learnerId],
  );

  return { data, loading, error, reload, create, creating, toggle };
}
