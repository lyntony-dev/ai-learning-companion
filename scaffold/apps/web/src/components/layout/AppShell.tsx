import { GraduationCap, MoonStars, Sun, UserCircle, SignOut, Chalkboard } from '@phosphor-icons/react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useTheme } from '@/lib/theme';
import { useRole, type Role } from '@/lib/role';
import { useAuth } from '@/lib/auth';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

// 导航按角色过滤:学生看不到教学洞察,讲师只看洞察。
// 角色由真实登录身份派生(梯队一),讲师视图受后端 require_teacher 保护。
const navItems: { to: string; label: string; roles: Role[] }[] = [
  { to: '/courses', label: '课程', roles: ['student'] },
  { to: '/student', label: '学生问答', roles: ['student'] },
  { to: '/training', label: '训练闭环', roles: ['student'] },
  { to: '/capstone', label: '项目陪练', roles: ['student'] },
  { to: '/archive', label: '学习档案', roles: ['student'] },
  { to: '/teacher', label: '教学洞察', roles: ['teacher'] },
];

export function AppShell() {
  const { theme, toggle } = useTheme();
  const { role } = useRole();
  const { isAuthed, session, signOut } = useAuth();
  const navigate = useNavigate();
  const items = navItems.filter((item) => item.roles.includes(role));

  const handleSignOut = () => {
    signOut();
    navigate('/student', { replace: true });
  };

  return (
    <div className="flex h-full flex-col">
      <header className="flex h-14 shrink-0 items-center gap-6 border-b border-[var(--color-border)] px-5">
        <div className="flex items-center gap-2 font-semibold">
          <GraduationCap size={20} weight="duotone" className="text-[var(--color-accent)]" />
          <span>AI 学习伙伴</span>
        </div>

        <nav className="flex items-center gap-1">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  'rounded-[var(--radius)] px-3 py-1.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-[var(--color-surface-2)] text-[var(--color-fg)]'
                    : 'text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]',
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-3">
          {isAuthed ? (
            <div className="flex items-center gap-1">
              {role === 'teacher' ? (
                <span className="flex items-center gap-1.5 rounded-[var(--radius)] bg-[var(--color-surface-2)] px-2.5 py-1.5 text-sm font-medium text-[var(--color-fg)]">
                  <Chalkboard size={18} weight="duotone" className="text-[var(--color-accent)]" />
                  {session?.display_name ?? '讲师'}
                </span>
              ) : (
                <NavLink
                  to="/profile"
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-1.5 rounded-[var(--radius)] px-2.5 py-1.5 text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-[var(--color-surface-2)] text-[var(--color-fg)]'
                        : 'text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]',
                    )
                  }
                >
                  <UserCircle size={18} weight="duotone" />
                  {session?.display_name ?? '我的画像'}
                </NavLink>
              )}
              <Button variant="ghost" size="icon" onClick={handleSignOut} aria-label="退出登录">
                <SignOut size={18} />
              </Button>
            </div>
          ) : (
            <Button variant="outline" size="sm" onClick={() => navigate('/login')}>
              登录
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggle}
            aria-label={theme === 'dark' ? '切换到浅色主题' : '切换到深色主题'}
          >
            {theme === 'dark' ? <Sun size={18} /> : <MoonStars size={18} />}
          </Button>
        </div>
      </header>

      <main className="min-h-0 flex-1">
        <Outlet />
      </main>
    </div>
  );
}
