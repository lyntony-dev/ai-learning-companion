/**
 * 真实 fetch 封装(替代脚手架里直接 throw 的占位)。
 * dev 环境经 Vite proxy 转发 /api → http://localhost:8000。
 */

import { getStoredToken } from '@/lib/auth';

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail || `请求失败(HTTP ${status})`);
    this.name = 'ApiError';
  }
}

const BASE = '/api';

/** 统一请求头:基础头 + 登录 token(ADR-0008)。未登录不带 Authorization,走访客态。 */
function buildHeaders(base: Record<string, string>): Record<string, string> {
  const token = getStoredToken();
  return token ? { ...base, Authorization: `Bearer ${token}` } : base;
}

async function parseError(res: Response): Promise<never> {
  let detail = '';
  try {
    const body = await res.json();
    detail = typeof body?.detail === 'string' ? body.detail : JSON.stringify(body?.detail ?? '');
  } catch {
    detail = res.statusText;
  }
  throw new ApiError(res.status, detail);
}

export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'GET',
    headers: buildHeaders({ Accept: 'application/json' }),
    signal,
  });
  if (!res.ok) await parseError(res);
  return res.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: buildHeaders({ 'Content-Type': 'application/json', Accept: 'application/json' }),
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) await parseError(res);
  return res.json() as Promise<T>;
}

export async function apiPatch<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PATCH',
    headers: buildHeaders({ 'Content-Type': 'application/json', Accept: 'application/json' }),
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) await parseError(res);
  return res.json() as Promise<T>;
}

/** 用于 204 无响应体的接口(如删除会话)。 */
export async function apiDelete(path: string, signal?: AbortSignal): Promise<void> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'DELETE',
    headers: buildHeaders({ Accept: 'application/json' }),
    signal,
  });
  if (!res.ok) await parseError(res);
}
