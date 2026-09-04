import * as Dialog from '@radix-ui/react-dialog';
import { ArrowSquareOut, X } from '@phosphor-icons/react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { contentUrl, fetchContentText, previewKind } from '@/api/courses';
import { ApiError } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/feedback/Skeleton';
import { ErrorState } from '@/components/feedback/ErrorState';
import { MarkdownView } from '@/components/preview/MarkdownView';
import type { PreviewTarget } from '@/components/preview/preview-context';

interface MaterialPreviewProps {
  target: PreviewTarget | null;
  onClose: () => void;
}

function isPdf(relPath: string): boolean {
  return relPath.toLowerCase().endsWith('.pdf');
}

/** 页码定位:优先 anchorValue(slide/page),回退旧 slideNo 字段。 */
function pageAnchor(target: PreviewTarget | null): number | null {
  if (!target) return null;
  if ((target.anchorType === 'slide' || target.anchorType === 'page') && target.anchorValue) {
    const n = Number(target.anchorValue);
    return Number.isFinite(n) && n >= 1 ? n : null;
  }
  return target.slideNo != null && target.slideNo >= 1 ? target.slideNo : null;
}

/**
 * 资料 / 课件预览抽屉:在应用内直接展示,不再跳新标签。
 * - html / pdf → iframe 内联渲染(后端已设 Content-Disposition: inline)
 * - md / 课件 → react-markdown 富文本
 * - py / txt → 代码块
 * 引用来源跳转定位(CoursewareDoc v1 anchorType):
 * - heading → markdown 里滚动到对应 slug id 的标题 + 高亮
 * - slide → HTML PPT 第 N 个 section;page → PDF #page=N
 * 四态:加载中(Skeleton)/ 错误(ErrorState + 重试)/ 成功 /(必有目标,无空态)。
 */
export function MaterialPreview({ target, onClose }: MaterialPreviewProps) {
  const open = target !== null;
  const kind = target ? previewKind(target.relPath) : 'iframe';
  const contentKind = target?.kind ?? 'material';

  const [text, setText] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    // iframe 类(html/pdf)由浏览器直接加载,不走 fetch。
    if (!target || kind === 'iframe') {
      setText(null);
      setError(null);
      return;
    }
    const ctrl = new AbortController();
    setLoading(true);
    setError(null);
    setText(null);
    fetchContentText(target.coursePackId, target.relPath, contentKind, ctrl.signal)
      .then(setText)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setError(err instanceof ApiError ? err.message : '内容加载失败。');
      })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, [target, kind, contentKind, reloadToken]);

  // Markdown/课件:文本渲染完成后,滚动到 heading anchor(slug id)并高亮。
  const anchorValue = target?.anchorValue;
  const anchorType = target?.anchorType;
  useEffect(() => {
    if (text === null || kind !== 'markdown') return;
    if (anchorType !== 'heading' || !anchorValue) return;
    // 等一帧,确保 react-markdown 已把标题 id 挂上。
    const raf = requestAnimationFrame(() => {
      const root = scrollRef.current;
      const el = root?.querySelector<HTMLElement>(`#${CSS.escape(anchorValue)}`);
      if (!el) return;
      el.scrollIntoView({ block: 'start' });
      el.classList.add('cited-heading');
    });
    return () => cancelAnimationFrame(raf);
  }, [text, kind, anchorType, anchorValue]);

  // HTML 课件同源(经 Vite proxy),iframe 加载完成后把第 N 个
  // <section data-mira-slide> 滚动进视图,实现引用来源直达指定页。
  const slidePage = pageAnchor(target);
  const scrollToSlide = useCallback(() => {
    if (slidePage == null) return;
    const doc = iframeRef.current?.contentDocument;
    if (!doc) return;
    const sections = doc.querySelectorAll('section[data-mira-slide]');
    const el = sections[slidePage - 1] as HTMLElement | undefined;
    if (el) {
      el.scrollIntoView({ block: 'start' });
      // 轻量高亮,提示这是被引用的一页。
      el.style.outline = '2px solid var(--color-accent)';
      el.style.outlineOffset = '4px';
    }
  }, [slidePage]);

  const base = target ? contentUrl(target.coursePackId, target.relPath, contentKind) : '';
  // PDF 用 #page=N 让浏览器内置阅读器直接跳页;HTML 走 iframe onLoad 定位。
  const url = target && isPdf(target.relPath) && slidePage != null ? `${base}#page=${slidePage}` : base;

  return (
    <Dialog.Root open={open} onOpenChange={(o) => !o && onClose()}>
      <AnimatePresence>
        {open && target ? (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild>
              <motion.div
                className="fixed inset-0 z-40 bg-black/30"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              />
            </Dialog.Overlay>
            <Dialog.Content asChild aria-describedby={undefined}>
              <motion.div
                className="fixed right-0 top-0 z-50 flex h-full w-full max-w-2xl flex-col border-l border-[var(--color-border)] bg-[var(--color-bg)] shadow-xl"
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                transition={{ type: 'spring', stiffness: 320, damping: 34 }}
              >
                <div className="flex items-center justify-between gap-3 border-b border-[var(--color-border)] p-4">
                  <div className="min-w-0">
                    <Dialog.Title className="truncate text-sm font-semibold">
                      {target.title}
                    </Dialog.Title>
                    <p className="truncate text-xs text-[var(--color-fg-muted)]">
                      {target.relPath}
                      {slidePage != null ? ` · 第 ${slidePage} 页` : ''}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    <a
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      title="在新标签打开"
                      className="flex h-9 w-9 items-center justify-center rounded-[var(--radius)] text-[var(--color-fg-muted)] transition-colors hover:bg-[var(--color-surface-2)] hover:text-[var(--color-fg)]"
                    >
                      <ArrowSquareOut size={16} />
                    </a>
                    <Button variant="ghost" size="icon" onClick={onClose} aria-label="关闭">
                      <X size={18} />
                    </Button>
                  </div>
                </div>

                <div className="min-h-0 flex-1 overflow-hidden">
                  {kind === 'iframe' ? (
                    <iframe
                      key={url}
                      ref={iframeRef}
                      src={url}
                      title={target.title}
                      onLoad={scrollToSlide}
                      className="h-full w-full border-0 bg-white"
                    />
                  ) : (
                    <div ref={scrollRef} className="h-full overflow-y-auto p-4">
                      {loading ? (
                        <div className="flex flex-col gap-2">
                          {[0, 1, 2, 3, 4].map((i) => (
                            <Skeleton key={i} className="h-4 w-full" />
                          ))}
                        </div>
                      ) : error ? (
                        <ErrorState
                          message={error}
                          onRetry={() => setReloadToken((n) => n + 1)}
                        />
                      ) : text !== null && kind === 'markdown' ? (
                        <MarkdownView text={text} />
                      ) : text !== null ? (
                        <pre className="overflow-x-auto rounded-[calc(var(--radius)-2px)] bg-[var(--color-surface-2)] p-3 font-mono text-xs leading-relaxed">
                          {text}
                        </pre>
                      ) : null}
                    </div>
                  )}
                </div>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        ) : null}
      </AnimatePresence>
    </Dialog.Root>
  );
}
