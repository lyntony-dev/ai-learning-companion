import { apiGet, apiPatch, apiPost } from './client';
import type {
  AccountResponse,
  AuthTokenResponse,
  LoginRequest,
  RegisterRequest,
  UpdateProfileRequest,
} from './types';

/** 注册:建身份+凭据+空画像,返回 token(ADR-0008)。 */
export function register(req: RegisterRequest, signal?: AbortSignal): Promise<AuthTokenResponse> {
  return apiPost<AuthTokenResponse>('/auth/register', req, signal);
}

/** 登录:校验密码,返回 token。 */
export function login(req: LoginRequest, signal?: AbortSignal): Promise<AuthTokenResponse> {
  return apiPost<AuthTokenResponse>('/auth/login', req, signal);
}

/** 当前登录学生的身份 + 画像 + 自动学习画像(需 token,由 client 统一注入)。 */
export function fetchAccount(signal?: AbortSignal): Promise<AccountResponse> {
  return apiGet<AccountResponse>('/auth/me', signal);
}

/** 更新画像(部分字段)。 */
export function updateProfile(
  req: UpdateProfileRequest,
  signal?: AbortSignal,
): Promise<AccountResponse> {
  return apiPatch<AccountResponse>('/auth/me', req, signal);
}
