import { describe, expect, it } from 'vitest';
import { splitBold } from '@/lib/inlineMarkdown';

describe('splitBold', () => {
  it('成对的 ** 拆成加粗片段', () => {
    expect(splitBold('1. **直接影响检索质量**:分块太大')).toEqual([
      { text: '1. ', bold: false },
      { text: '直接影响检索质量', bold: true },
      { text: ':分块太大', bold: false },
    ]);
  });

  it('不成对的星号原样保留', () => {
    expect(splitBold('乘法用 * 号,**没闭合')).toEqual([{ text: '乘法用 * 号,**没闭合', bold: false }]);
  });

  it('加粗不跨行', () => {
    expect(splitBold('**第一行\n第二行**')).toEqual([{ text: '**第一行\n第二行**', bold: false }]);
  });

  it('空串返回空数组', () => {
    expect(splitBold('')).toEqual([]);
  });
});
