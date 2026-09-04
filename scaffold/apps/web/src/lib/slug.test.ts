import { describe, expect, it } from 'vitest';
import { extractExplicitAnchor, headingAnchor, slugify } from '@/lib/slug';

// 与后端 apps/api/tests/test_slug.py 一一对应,守护前后端锚点行为对齐。
describe('slugify', () => {
  it('basic ascii → 小写连字符', () => {
    expect(slugify('What You Learn')).toBe('what-you-learn');
  });

  it('中文保留', () => {
    expect(slugify('这个项目学什么')).toBe('这个项目学什么');
  });

  it('混合与标点', () => {
    expect(slugify('3.1 LLM 是什么?')).toBe('3-1-llm-是什么');
  });

  it('合并并裁剪首尾连字符', () => {
    expect(slugify('  --Hello___World--  ')).toBe('hello-world');
  });
});

describe('extractExplicitAnchor', () => {
  it('剥离显式锚点', () => {
    expect(extractExplicitAnchor('核心概念 {#core-concepts}')).toEqual(['核心概念', 'core-concepts']);
  });

  it('无显式锚点返回 null', () => {
    expect(extractExplicitAnchor('核心概念')).toEqual(['核心概念', null]);
  });
});

describe('headingAnchor', () => {
  it('显式锚点优先', () => {
    expect(headingAnchor('介绍 {#intro}')).toEqual(['介绍', 'intro']);
  });

  it('无显式锚点回退到 slug', () => {
    expect(headingAnchor('Getting Started')).toEqual(['Getting Started', 'getting-started']);
  });
});
