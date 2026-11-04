export interface InlineSegment {
  text: string;
  bold: boolean;
}

const BOLD = /\*\*(.+?)\*\*/g;

/**
 * 把一行文本里成对的 **加粗** 拆成片段,供组件渲染成 <strong>。
 * 只认同一行里成对的标记;不成对的星号原样保留,不吞字。
 */
export function splitBold(text: string): InlineSegment[] {
  const segments: InlineSegment[] = [];
  let last = 0;
  let match: RegExpExecArray | null;

  BOLD.lastIndex = 0;
  while ((match = BOLD.exec(text)) !== null) {
    if (match.index > last) segments.push({ text: text.slice(last, match.index), bold: false });
    segments.push({ text: match[1], bold: true });
    last = match.index + match[0].length;
  }
  if (last < text.length) segments.push({ text: text.slice(last), bold: false });
  return segments;
}
