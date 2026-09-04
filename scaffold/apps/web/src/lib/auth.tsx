/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';

/** 登录会话(ADR-0008)。未登录时为 null,数据走访客态 demo_user。 */
export interface AuthSession {
  learner_id: string;
  username: string;
  display_name: string;
  role: 'student' | 'teacher';
  token: string;
}

interface AuthContextValue {
  session: AuthSession | null;
  /** 有效学习者 id:登录则为本人,否则访客 demo_user。 */
  learnerId: string;
  isAuthed: boolean;
  /** 登录账号的角色;未登录默认 student(访客只体验学生态)。 */
  role: 'student' | 'teacher';
  signIn: (session: AuthSession) => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const STORAGE_KEY = 'ai-tutor-auth';
export const GUEST_LEARNER_ID = 'demo_user';

function readInitialSession(): AuthSession | null {
  if (typeof window === 'undefined') return null;
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (!stored) return null;
  try {
    const parsed = JSON.parse(stored) as AuthSession;
    if (parsed && parsed.token && parsed.learner_id) {
      // 兼容旧持久化(无 role 字段):按 learner_id 前缀派生
      if (parsed.role !== 'teacher' && parsed.role !== 'student') {
        parsed.role = parsed.learner_id.startsWith('tea_') ? 'teacher' : 'student';
      }
      return parsed;
    }
  } catch {
    /* 损坏的持久化数据,忽略 */
  }
  return null;
}

/** 登录态:localStorage 持久化,刷新后恢复(镜像 theme.tsx 范式)。 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(readInitialSession);

  useEffect(() => {
    if (session) {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    } else {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  }, [session]);

  const signIn = useCallback((next: AuthSession) => setSession(next), []);
  const signOut = useCallback(() => setSession(null), []);

  return (
    <AuthContext.Provider
      value={{
        session,
        learnerId: session?.learner_id ?? GUEST_LEARNER_ID,
        isAuthed: session !== null,
        role: session?.role ?? 'student',
        signIn,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

/** 供非组件模块(api client)读取当前 token 注入 Authorization 头。 */
export function getStoredToken(): string | null {
  return readInitialSession()?.token ?? null;
}
