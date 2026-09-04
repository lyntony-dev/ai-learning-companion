import { lazy, Suspense } from 'react';
import { Navigate, Outlet, Route, Routes } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { useRole, type Role } from './lib/role';
import { useAuth } from './lib/auth';
import { Skeleton } from './components/feedback/Skeleton';

/**
 * 路由级代码分割(Tier 3-7):每个页面拆为独立 chunk,按需加载。
 * 命名导出经 .then 映射为 default,满足 React.lazy 约定。
 */
const StudentPage = lazy(() => import('./routes/student').then((m) => ({ default: m.StudentPage })));
const TeacherPage = lazy(() => import('./routes/teacher').then((m) => ({ default: m.TeacherPage })));
const TrainingPage = lazy(() =>
  import('./routes/training').then((m) => ({ default: m.TrainingPage })),
);
const CapstonePage = lazy(() =>
  import('./routes/capstone').then((m) => ({ default: m.CapstonePage })),
);
const CoursesPage = lazy(() => import('./routes/courses').then((m) => ({ default: m.CoursesPage })));
const CourseDetailPage = lazy(() =>
  import('./routes/course-detail').then((m) => ({ default: m.CourseDetailPage })),
);
const LoginPage = lazy(() => import('./routes/login').then((m) => ({ default: m.LoginPage })));
const ProfilePage = lazy(() =>
  import('./routes/profile').then((m) => ({ default: m.ProfilePage })),
);
const ArchivePage = lazy(() =>
  import('./routes/archive').then((m) => ({ default: m.ArchivePage })),
);

/** 懒加载页面切换时的占位骨架,匹配主内容区留白。 */
function RouteFallback() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-6">
      <Skeleton className="h-8 w-48" />
      <div className="mt-4 flex flex-col gap-4">
        <Skeleton className="h-32" />
        <Skeleton className="h-40" />
      </div>
    </div>
  );
}

/**
 * 角色守卫(梯队一:真实身份派生)。
 * - 需要 teacher 但未登录 → 去登录页(讲师视图受后端 require_teacher 保护)。
 * - 角色不符 → 跳到当前角色的主视图。
 */
function RequireRole({ role: required, children }: { role: Role; children: React.ReactNode }) {
  const { role } = useRole();
  const { isAuthed } = useAuth();
  if (role !== required) {
    if (required === 'teacher' && !isAuthed) {
      return <Navigate to="/login" replace />;
    }
    return <Navigate to={role === 'teacher' ? '/teacher' : '/student'} replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route
          element={
            <Suspense fallback={<RouteFallback />}>
              <Outlet />
            </Suspense>
          }
        >
          <Route path="/" element={<Navigate to="/student" replace />} />
          <Route
            path="/courses"
            element={
              <RequireRole role="student">
                <CoursesPage />
              </RequireRole>
            }
          />
          <Route
            path="/courses/:coursePackId"
            element={
              <RequireRole role="student">
                <CourseDetailPage />
              </RequireRole>
            }
          />
          <Route path="/student" element={<StudentPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route
            path="/teacher"
            element={
              <RequireRole role="teacher">
                <TeacherPage />
              </RequireRole>
            }
          />
          <Route
            path="/training"
            element={
              <RequireRole role="student">
                <TrainingPage />
              </RequireRole>
            }
          />
          <Route
            path="/capstone"
            element={
              <RequireRole role="student">
                <CapstonePage />
              </RequireRole>
            }
          />
          <Route
            path="/archive"
            element={
              <RequireRole role="student">
                <ArchivePage />
              </RequireRole>
            }
          />
          <Route path="*" element={<Navigate to="/student" replace />} />
        </Route>
      </Route>
    </Routes>
  );
}
