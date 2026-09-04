import type { ReactNode } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { headingAnchor } from '../../lib/slug';

/** 从渲染子节点里抽纯文本,用于算标题 anchor(与后端 slug 对齐)。 */
function childrenText(children: ReactNode): string {
  if (children == null || typeof children === 'boolean') return '';
  if (typeof children === 'string' || typeof children === 'number') return String(children);
  if (Array.isArray(children)) return children.map(childrenText).join('');
  // React 元素:递归其 props.children
  const el = children as { props?: { children?: ReactNode } };
  if (el.props && 'children' in el.props) return childrenText(el.props.children);
  return '';
}

/** 标题:算 slug id(供锚点跳转)+ 剥离 `{#anchor}` 显式标记不外显。 */
function heading(level: number, children: ReactNode) {
  const raw = childrenText(children);
  const [clean, anchor] = headingAnchor(raw);
  // 若标题含显式 {#anchor},children 里会带该标记文本;用清洗后的纯文本渲染。
  const hasExplicit = clean !== raw.trim();
  const content = hasExplicit ? clean : children;
  const cls =
    level <= 1
      ? 'mt-2 text-lg font-semibold'
      : level === 2
        ? 'mt-3 text-base font-semibold'
        : 'mt-1 font-semibold';
  const Tag = `h${Math.min(level, 6)}` as 'h1';
  return (
    <Tag id={anchor} className={`scroll-mt-4 ${cls}`}>
      {content}
    </Tag>
  );
}

/**
 * Markdown 渲染:react-markdown + GFM。样式全走设计 token,不引额外硬编码色。
 * 标题带 slug id(与后端锚点同源),支持引用来源/目录跳转到具体标题段。
 * 用于资料预览抽屉里的 .md / 课件文件。
 */
export function MarkdownView({ text }: { text: string }) {
  return (
    <div className="flex flex-col gap-3 text-sm leading-relaxed text-[var(--color-fg)]">
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => heading(1, children),
          h2: ({ children }) => heading(2, children),
          h3: ({ children }) => heading(3, children),
          h4: ({ children }) => heading(4, children),
          h5: ({ children }) => heading(5, children),
          h6: ({ children }) => heading(6, children),
          p: ({ children }) => <p>{children}</p>,
          ul: ({ children }) => (
            <ul className="ml-5 list-disc space-y-1">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="ml-5 list-decimal space-y-1">{children}</ol>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[var(--color-accent)] underline underline-offset-2"
            >
              {children}
            </a>
          ),
          code: ({ children }) => (
            <code className="rounded bg-[var(--color-surface-2)] px-1 py-0.5 font-mono text-[0.85em]">
              {children}
            </code>
          ),
          pre: ({ children }) => (
            <pre className="overflow-x-auto rounded-[calc(var(--radius)-2px)] bg-[var(--color-surface-2)] p-3 font-mono text-xs">
              {children}
            </pre>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-[var(--color-border)] pl-3 text-[var(--color-fg-muted)]">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <table className="w-full border-collapse text-xs">{children}</table>
          ),
          th: ({ children }) => (
            <th className="border border-[var(--color-border)] px-2 py-1 text-left font-medium">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-[var(--color-border)] px-2 py-1">{children}</td>
          ),
        }}
      >
        {text}
      </Markdown>
    </div>
  );
}
