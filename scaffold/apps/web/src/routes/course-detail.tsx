import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  BookOpen,
  Code,
  Eye,
  FileText,
  ListBullets,
  Paperclip,
  Presentation,
} from '@phosphor-icons/react';
import { getCoursePack } from '@/api/courses';
import { ApiError } from '@/api/client';
import { usePreview } from '@/components/preview/preview-context';
import type {
  CoursePackDetailResponse,
  CourseSummary,
  CoursewareRef,
  MaterialRef,
} from '@/api/types';

function materialIcon(kind: string) {
  if (kind === 'slide') return Presentation;
  if (kind === 'code_example') return Code;
  if (kind === 'attachment') return Paperclip;
  return FileText;
}

/** 结构化课件主体:打开正文按钮 + 章节目录(点击跳转到对应标题段)。 */
function CoursewareBlock({
  coursePackId,
  courseName,
  courseware,
}: {
  coursePackId: string;
  courseName: string;
  courseware: CoursewareRef;
}) {
  const { open } = usePreview();
  const openAt = (anchor?: string) =>
    open({
      coursePackId,
      relPath: courseware.rel_path,
      title: courseware.title || courseName,
      kind: 'courseware',
      anchorType: anchor ? 'heading' : undefined,
      anchorValue: anchor,
    });

  return (
    <div className="flex flex-col gap-3">
      <button
        type="button"
        onClick={() => openAt()}
        className="group flex items-center gap-2 rounded-[var(--radius)] border border-[var(--color-accent)] bg-[var(--color-accent-soft)] px-3 py-2 text-left text-sm font-medium text-[var(--color-accent)] transition-colors hover:brightness-105"
      >
        <BookOpen size={16} className="shrink-0" />
        <span className="min-w-0 flex-1 truncate">进入课件 · {courseware.title || courseName}</span>
        <Eye size={15} className="shrink-0 opacity-0 transition-opacity group-hover:opacity-100" />
      </button>

      {courseware.sections.length > 0 ? (
        <div>
          <p className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-[var(--color-fg-muted)]">
            <ListBullets size={13} />
            课件目录
          </p>
          <ul className="flex flex-col gap-0.5">
            {courseware.sections.map((s) => (
              <li key={s.anchor}>
                <button
                  type="button"
                  onClick={() => openAt(s.anchor)}
                  className="block w-full truncate rounded-[var(--radius)] px-2 py-1 text-left text-sm text-[var(--color-fg)] transition-colors hover:bg-[var(--color-surface-2)]"
                >
                  {s.title}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

/** 资料/附件清单项:应用内预览打开。 */
function MaterialItem({
  coursePackId,
  material,
}: {
  coursePackId: string;
  material: MaterialRef;
}) {
  const { open } = usePreview();
  const Icon = materialIcon(material.kind);
  return (
    <button
      type="button"
      onClick={() =>
        open({ coursePackId, relPath: material.rel_path, title: material.title })
      }
      className="group flex w-full items-center gap-2 rounded-[var(--radius)] px-2 py-1.5 text-left text-sm transition-colors hover:bg-[var(--color-surface-2)]"
    >
      <Icon size={15} className="shrink-0 text-[var(--color-fg-muted)]" />
      <span className="min-w-0 flex-1 truncate">{material.title}</span>
      <span className="truncate text-xs text-[var(--color-fg-muted)]">{material.rel_path}</span>
      <Eye
        size={14}
        className="shrink-0 text-[var(--color-fg-muted)] opacity-0 transition-opacity group-hover:opacity-100"
      />
    </button>
  );
}

function CourseCard({ pack, course }: { pack: CoursePackDetailResponse; course: CourseSummary }) {
  const hasCourseware = Boolean(course.courseware);
  return (
    <section className="rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <h2 className="mb-3 font-medium">{course.name}</h2>

      {course.courseware ? (
        <CoursewareBlock
          coursePackId={pack.course_pack_id}
          courseName={course.name}
          courseware={course.courseware}
        />
      ) : null}

      {course.materials.length > 0 ? (
        <div className={hasCourseware ? 'mt-4 border-t border-[var(--color-border)] pt-3' : ''}>
          {hasCourseware ? (
            <p className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-[var(--color-fg-muted)]">
              <Paperclip size={13} />
              原始资料附件
            </p>
          ) : null}
          <ul className="flex flex-col gap-1.5">
            {course.materials.map((m) => (
              <li key={`${m.kind}:${m.rel_path}`}>
                <MaterialItem coursePackId={pack.course_pack_id} material={m} />
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

export function CourseDetailPage() {
  const { coursePackId = '' } = useParams();
  const [pack, setPack] = useState<CoursePackDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    setPack(null);
    setError(null);
    getCoursePack(coursePackId, ctrl.signal)
      .then(setPack)
      .catch((err) => {
        if (ctrl.signal.aborted) return;
        setError(err instanceof ApiError ? err.message : '课程加载失败');
      });
    return () => ctrl.abort();
  }, [coursePackId]);

  return (
    <div className="mx-auto h-full max-w-3xl overflow-y-auto px-6 py-8">
      <Link
        to="/courses"
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-[var(--color-fg-muted)] transition-colors hover:text-[var(--color-fg)]"
      >
        <ArrowLeft size={15} />
        返回课程列表
      </Link>

      {error ? (
        <p className="text-sm text-[var(--color-unknown)]">{error}</p>
      ) : pack === null ? (
        <p className="text-sm text-[var(--color-fg-muted)]">加载中…</p>
      ) : (
        <>
          <h1 className="mb-1 text-xl font-semibold">{pack.name}</h1>
          <p className="mb-6 text-sm text-[var(--color-fg-muted)]">{pack.description}</p>

          <div className="flex flex-col gap-5">
            {pack.courses.map((course) => (
              <CourseCard key={course.course_id} pack={pack} course={course} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
