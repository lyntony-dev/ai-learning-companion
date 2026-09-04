import { defineConfig } from 'vitest/config';
import path from 'node:path';

// 前端单测(Tier 3-7):纯逻辑函数为主(slug 须与后端行为对齐)。
// node 环境足够;涉及 DOM 的组件测试后续按需切 jsdom。
export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
});
