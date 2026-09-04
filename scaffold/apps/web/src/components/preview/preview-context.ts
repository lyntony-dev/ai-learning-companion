import { createContext, useContext } from 'react';

/** 预览目标:课程包内一份资料。
 *  - kind='material'(默认):relPath 相对 materials/;slideNo 页码提示。
 *  - kind='courseware':relPath 相对 courseware/;anchorValue 为标题 slug。
 *  anchorType/anchorValue 统一承载定位:heading→slug,slide/page→页码。
 */
export interface PreviewTarget {
  coursePackId: string;
  relPath: string;
  title: string;
  kind?: 'material' | 'courseware';
  slideNo?: number | null;
  anchorType?: string;
  anchorValue?: string;
}

export interface PreviewContextValue {
  open: (target: PreviewTarget) => void;
}

export const PreviewContext = createContext<PreviewContextValue | null>(null);

export function usePreview(): PreviewContextValue {
  const ctx = useContext(PreviewContext);
  if (!ctx) throw new Error('usePreview 必须在 PreviewProvider 内使用');
  return ctx;
}
