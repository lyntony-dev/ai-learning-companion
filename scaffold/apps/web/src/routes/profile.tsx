import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { Navigate } from 'react-router-dom';
import { UserCircle } from '@phosphor-icons/react';
import { fetchAccount, updateProfile } from '@/api/auth';
import { ApiError } from '@/api/client';
import type { AccountResponse, ProfileFields } from '@/api/types';
import { useAuth } from '@/lib/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/feedback/Skeleton';
import { ErrorState } from '@/components/feedback/ErrorState';

const DIFFICULTY_OPTIONS = [
  { value: '', label: '未设置' },
  { value: 'easy', label: '循序渐进' },
  { value: 'medium', label: '适中' },
  { value: 'hard', label: '挑战' },
];

/** 我的画像(ADR-0008):基础资料 + 学习目标偏好(可编辑) + 自动画像(只读)。 */
export function ProfilePage() {
  const { isAuthed, signOut } = useAuth();
  const [account, setAccount] = useState<AccountResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<ProfileFields | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchAccount()
      .then((res) => {
        setAccount(res);
        setForm(res.profile);
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : '加载画像失败,请重试。');
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (isAuthed) load();
  }, [isAuthed, load]);

  if (!isAuthed) return <Navigate to="/login" replace />;

  const handleChange = <K extends keyof ProfileFields>(key: K, value: ProfileFields[K]) => {
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev));
    setSaved(false);
  };

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    if (!form || saving) return;
    setSaving(true);
    setError(null);
    try {
      const res = await updateProfile({
        nickname: form.nickname,
        avatar: form.avatar,
        background: form.background,
        learning_goal: form.learning_goal,
        weekly_hours: form.weekly_hours,
        preferred_difficulty: form.preferred_difficulty,
      });
      setAccount(res);
      setForm(res.profile);
      setSaved(true);
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : '保存失败,请重试。');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto h-full max-w-2xl overflow-y-auto px-6 py-6">
      <div className="mb-5 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--color-surface-2)] text-[var(--color-accent)]">
            <UserCircle size={22} weight="duotone" />
          </div>
          <div>
            <h1 className="text-lg font-semibold">我的画像</h1>
            {account ? (
              <p className="text-sm text-[var(--color-fg-muted)]">
                {account.display_name} · @{account.username}
              </p>
            ) : null}
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={signOut}>
          退出登录
        </Button>
      </div>

      {loading ? (
        <div className="flex flex-col gap-4">
          <Skeleton className="h-48" />
          <Skeleton className="h-56" />
          <Skeleton className="h-28" />
        </div>
      ) : null}

      {error && !loading && !account ? (
        <Card>
          <CardContent className="pt-5">
            <div className="h-52">
              <ErrorState message={error} onRetry={load} />
            </div>
          </CardContent>
        </Card>
      ) : null}

      {account && form && !loading ? (
        <form className="flex flex-col gap-4" onSubmit={handleSave}>
          {/* 基础资料 */}
          <Card>
            <CardHeader>
              <CardTitle>基础资料</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <Field label="昵称">
                <Input
                  value={form.nickname}
                  onChange={(e) => handleChange('nickname', e.target.value)}
                  placeholder="展示名"
                />
              </Field>
              <Field label="头像 URL">
                <Input
                  value={form.avatar}
                  onChange={(e) => handleChange('avatar', e.target.value)}
                  placeholder="https://…(可选)"
                />
              </Field>
              <Field label="背景介绍">
                <textarea
                  value={form.background}
                  onChange={(e) => handleChange('background', e.target.value)}
                  rows={3}
                  placeholder="你的专业、基础或学习背景"
                  className="w-full resize-none rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-fg)] outline-none placeholder:text-[var(--color-fg-muted)] focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--color-bg)]"
                />
              </Field>
            </CardContent>
          </Card>

          {/* 学习目标偏好 */}
          <Card>
            <CardHeader>
              <CardTitle>学习目标偏好</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <Field label="学习目标">
                <textarea
                  value={form.learning_goal}
                  onChange={(e) => handleChange('learning_goal', e.target.value)}
                  rows={2}
                  placeholder="你希望通过课程达成什么"
                  className="w-full resize-none rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-fg)] outline-none placeholder:text-[var(--color-fg-muted)] focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--color-bg)]"
                />
              </Field>
              <Field label="每周投入(小时)">
                <Input
                  type="number"
                  min={0}
                  max={168}
                  value={form.weekly_hours}
                  onChange={(e) => handleChange('weekly_hours', Number(e.target.value) || 0)}
                />
              </Field>
              <Field label="偏好难度">
                <select
                  value={form.preferred_difficulty}
                  onChange={(e) => handleChange('preferred_difficulty', e.target.value)}
                  className="h-10 w-full rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 text-sm text-[var(--color-fg)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--color-bg)]"
                >
                  {DIFFICULTY_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </Field>
            </CardContent>
          </Card>

          {/* 自动画像(只读) */}
          <Card>
            <CardHeader>
              <CardTitle>自动学习画像</CardTitle>
              <p className="text-xs text-[var(--color-fg-muted)]">
                依你的训练与作答自动统计,不可手动编辑
              </p>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Badge tone="known">已掌握 {account.auto_profile.known}</Badge>
              <Badge tone="fuzzy">模糊 {account.auto_profile.fuzzy}</Badge>
              <Badge tone="unknown">待巩固 {account.auto_profile.unknown}</Badge>
              <Badge tone="neutral">覆盖知识点 {account.auto_profile.topics_tracked}</Badge>
            </CardContent>
          </Card>

          {error ? (
            <div className="rounded-[var(--radius)] border border-[color-mix(in_srgb,var(--color-unknown)_40%,transparent)] bg-[color-mix(in_srgb,var(--color-unknown)_8%,transparent)] px-3 py-2 text-sm text-[var(--color-unknown)]">
              {error}
            </div>
          ) : null}

          <div className="flex items-center justify-end gap-3">
            {saved ? (
              <span className="text-sm text-[var(--color-known)]">已保存</span>
            ) : null}
            <Button type="submit" disabled={saving}>
              {saving ? '保存中…' : '保存画像'}
            </Button>
          </div>
        </form>
      ) : null}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs text-[var(--color-fg-muted)]">{label}</label>
      {children}
    </div>
  );
}
