/* eslint-disable react-refresh/only-export-components */
import { type ReactNode } from 'react';
import { useAuth } from '@/lib/auth';

export type Role = 'student' | 'teacher';

/**
 * 角色由**真实登录身份**派生(梯队一,取代 demo 无鉴权切换):
 * - 讲师账号(tea_*)→ teacher,可见教学洞察;
 * - 学生账号 / 访客 → student。
 *
 * 讲师视图受后端 require_teacher 保护,前端角色仅决定导航/路由可见性,
 * 真正的数据访问权限以后端 token 校验为准(不可前端伪造)。
 */
export function RoleProvider({ children }: { children: ReactNode }) {
  return <>{children}</>;
}

export function useRole() {
  const { role } = useAuth();
  return { role };
}
