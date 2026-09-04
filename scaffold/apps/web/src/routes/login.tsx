import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { GraduationCap } from '@phosphor-icons/react';
import { login, register } from '@/api/auth';
import { ApiError } from '@/api/client';
import { useAuth } from '@/lib/auth';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

type Mode = 'login' | 'register';
type Role = 'student' | 'teacher';

/** 登录 / 注册(ADR-0008 + 梯队一讲师账号)。学生用户名+密码;讲师注册需邀请码。 */
export function LoginPage() {
  const navigate = useNavigate();
  const { signIn } = useAuth();
  const [mode, setMode] = useState<Mode>('login');
  const [role, setRole] = useState<Role>('student');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [inviteCode, setInviteCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const user = username.trim();
    if (!user || !password || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const res =
        mode === 'login'
          ? await login({ username: user, password })
          : await register({
              username: user,
              password,
              display_name: displayName.trim() || undefined,
              role,
              invite_code: role === 'teacher' ? inviteCode.trim() : undefined,
            });
      signIn({
        learner_id: res.learner_id,
        username: res.username,
        display_name: res.display_name,
        role: res.role,
        token: res.token,
      });
      navigate(res.role === 'teacher' ? '/teacher' : '/student', { replace: true });
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : '请求失败,请重试。');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex h-full items-center justify-center px-6 py-10">
      <Card className="w-full max-w-sm">
        <CardHeader className="items-center text-center">
          <div className="mx-auto mb-1 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-surface-2)] text-[var(--color-accent)]">
            <GraduationCap size={24} weight="duotone" />
          </div>
          <CardTitle className="text-base">
            {mode === 'login' ? '登录 AI 学习伙伴' : '注册 AI 学习伙伴'}
          </CardTitle>
          <p className="text-sm text-[var(--color-fg-muted)]">
            {role === 'teacher' ? '讲师端可查看全班学情洞察' : '登录后可保存你的学习画像与掌握进度'}
          </p>
        </CardHeader>
        <CardContent>
          {mode === 'register' ? (
            <div className="mb-3 flex items-center gap-0.5 rounded-[var(--radius)] bg-[var(--color-surface-2)] p-0.5">
              {(['student', 'teacher'] as Role[]).map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => {
                    setRole(r);
                    setError(null);
                  }}
                  className={cn(
                    'flex-1 rounded-[calc(var(--radius)-2px)] px-2.5 py-1 text-sm font-medium transition-colors',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]',
                    role === r
                      ? 'bg-[var(--color-bg)] text-[var(--color-fg)] shadow-sm'
                      : 'text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]',
                  )}
                  aria-pressed={role === r}
                >
                  {r === 'student' ? '我是学生' : '我是讲师'}
                </button>
              ))}
            </div>
          ) : null}
          <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-[var(--color-fg-muted)]">用户名</label>
              <Input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="2-32 位字母、数字、下划线或中文"
                autoComplete="username"
                autoFocus
              />
            </div>
            {mode === 'register' ? (
              <div className="flex flex-col gap-1.5">
                <label className="text-xs text-[var(--color-fg-muted)]">昵称(可选)</label>
                <Input
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="展示名,留空则用用户名"
                />
              </div>
            ) : null}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-[var(--color-fg-muted)]">密码</label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="至少 6 位"
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              />
            </div>
            {mode === 'register' && role === 'teacher' ? (
              <div className="flex flex-col gap-1.5">
                <label className="text-xs text-[var(--color-fg-muted)]">讲师邀请码</label>
                <Input
                  value={inviteCode}
                  onChange={(e) => setInviteCode(e.target.value)}
                  placeholder="向课程管理员获取"
                  autoComplete="off"
                />
              </div>
            ) : null}

            {error ? (
              <div className="rounded-[var(--radius)] border border-[color-mix(in_srgb,var(--color-unknown)_40%,transparent)] bg-[color-mix(in_srgb,var(--color-unknown)_8%,transparent)] px-3 py-2 text-sm text-[var(--color-unknown)]">
                {error}
              </div>
            ) : null}

            <Button type="submit" disabled={submitting || !username.trim() || !password}>
              {submitting ? '处理中…' : mode === 'login' ? '登录' : '注册并登录'}
            </Button>
          </form>

          <div className="mt-4 text-center text-xs text-[var(--color-fg-muted)]">
            {mode === 'login' ? '还没有账号?' : '已有账号?'}
            <button
              type="button"
              className="ml-1 font-medium text-[var(--color-accent)] hover:underline"
              onClick={() => {
                setMode(mode === 'login' ? 'register' : 'login');
                setError(null);
              }}
            >
              {mode === 'login' ? '注册新账号' : '去登录'}
            </button>
          </div>
          <p className="mt-3 text-center text-xs text-[var(--color-fg-muted)]">
            无需登录也可以访客身份直接体验学生功能
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
