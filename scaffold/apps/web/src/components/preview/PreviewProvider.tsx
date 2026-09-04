import { useCallback, useMemo, useState } from 'react';
import { MaterialPreview } from '@/components/preview/MaterialPreview';
import {
  PreviewContext,
  type PreviewTarget,
} from '@/components/preview/preview-context';

/**
 * 资料预览抽屉的全局挂载点。任意组件经 usePreview().open(target) 触发,
 * 避免逐层透传。抽屉本身复用 Radix Dialog(仿 LearnerDrawer)。
 */
export function PreviewProvider({ children }: { children: React.ReactNode }) {
  const [target, setTarget] = useState<PreviewTarget | null>(null);
  const open = useCallback((next: PreviewTarget) => setTarget(next), []);
  const value = useMemo(() => ({ open }), [open]);

  return (
    <PreviewContext.Provider value={value}>
      {children}
      <MaterialPreview target={target} onClose={() => setTarget(null)} />
    </PreviewContext.Provider>
  );
}
