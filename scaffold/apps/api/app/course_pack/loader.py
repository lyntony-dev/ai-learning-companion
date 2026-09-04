"""CoursePackLoader (ADR-0006 / DESIGN §6)。

按约定目录 data/course_packs/<id>/ 读取 manifest/taxonomy/rubric,
产出统一 CoursePack 对象。加新课 = 放新目录,引擎零改动。

约定目录结构:
  <id>/
    manifest.yaml     # 必需:课程列表 + 里程碑序列
    taxonomy.yaml     # 可选:知识点树(候选)
    rubric.yaml       # 可选:批改标准(候选)
    questions/        # 可选:题库(feat-004/007 使用)
    courseware/       # 可选:结构化课件 (CoursewareDoc v1),课程主体
    materials/        # 原始资料(HTML PPT / MD / PDF),课件的附件来源
"""

from __future__ import annotations

from pathlib import Path

import yaml

from app.course_pack.schema import (
    ArtifactStatus,
    Attachment,
    Capstone,
    Course,
    CourseMaterials,
    CoursePack,
    CourseRubric,
    Courseware,
    Milestone,
    Question,
    QuestionDifficulty,
    QuestionSet,
    Rubric,
    RubricDimension,
    Taxonomy,
    Topic,
)

# 默认课程包根目录(相对 repo 根)。loader.py 在 app/course_pack/ 下,
# parents: [0]course_pack [1]app [2]api [3]apps [4]scaffold [5]repo根
DEFAULT_PACKS_ROOT = Path(__file__).resolve().parents[5] / "data" / "course_packs"


class CoursePackError(ValueError):
    """课程包结构或内容非法。"""


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def _read_frontmatter(path: Path) -> dict:
    """读 Markdown 文件头部的 YAML frontmatter(--- ... ---),无则返回 {}。"""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    data = yaml.safe_load(parts[1])
    return data if isinstance(data, dict) else {}


class CoursePackLoader:
    """把约定目录解析为 CoursePack 对象。"""

    def __init__(self, packs_root: Path | str | None = None) -> None:
        self.packs_root = Path(packs_root) if packs_root else DEFAULT_PACKS_ROOT

    def pack_dir(self, course_pack_id: str) -> Path:
        return self.packs_root / course_pack_id

    def available_packs(self) -> list[str]:
        if not self.packs_root.exists():
            return []
        return sorted(
            p.name
            for p in self.packs_root.iterdir()
            if p.is_dir() and (p / "manifest.yaml").exists()
        )

    def load(self, course_pack_id: str) -> CoursePack:
        pack_dir = self.pack_dir(course_pack_id)
        manifest_path = pack_dir / "manifest.yaml"
        if not manifest_path.exists():
            raise CoursePackError(
                f"课程包 '{course_pack_id}' 缺少 manifest.yaml (查找路径: {manifest_path})"
            )

        manifest = _load_yaml(manifest_path)
        declared_id = manifest.get("course_pack_id")
        if declared_id and declared_id != course_pack_id:
            raise CoursePackError(
                f"manifest course_pack_id='{declared_id}' 与目录名 '{course_pack_id}' 不一致"
            )

        courses = self._parse_courses(manifest.get("courses", []), pack_dir)
        capstone = self._parse_capstone(manifest.get("capstone"))
        taxonomy = self._parse_taxonomy(_load_yaml(pack_dir / "taxonomy.yaml"))
        rubric = self._parse_rubric(_load_yaml(pack_dir / "rubric.yaml"))
        questions = self._parse_questions(pack_dir / "questions", taxonomy)

        return CoursePack(
            course_pack_id=course_pack_id,
            name=manifest.get("name", course_pack_id),
            description=manifest.get("description", ""),
            version=manifest.get("version", "v1"),
            courses=courses,
            capstone=capstone,
            taxonomy=taxonomy,
            rubric=rubric,
            questions=questions,
        )

    # --- 解析辅助 ---

    def _parse_courses(self, raw: list, pack_dir: Path) -> list[Course]:
        courses: list[Course] = []
        materials_root = pack_dir / "materials"
        courseware_root = pack_dir / "courseware"
        for item in raw:
            mats_raw = item.get("materials", {}) or {}
            materials = CourseMaterials(
                lecture_note=mats_raw.get("lecture_note"),
                slides=mats_raw.get("slides", []) or [],
                code_examples=mats_raw.get("code_examples"),
            )
            self._verify_materials_exist(item.get("course_id", "?"), materials, materials_root)
            courseware = self._parse_courseware(
                item.get("course_id", "?"),
                item.get("courseware"),
                courseware_root,
                materials_root,
            )
            courses.append(
                Course(
                    course_id=item["course_id"],
                    name=item.get("name", item["course_id"]),
                    materials=materials,
                    courseware=courseware,
                )
            )
        return courses

    def _parse_courseware(
        self,
        course_id: str,
        rel: str | None,
        courseware_root: Path,
        materials_root: Path,
    ) -> Courseware | None:
        """解析结构化课件声明。rel 为 manifest 里相对 courseware/ 的路径。

        课件正文头部 YAML frontmatter 提供 title / version / attachments。
        校验课件文件与其声明的附件真实存在(fail fast)。
        """
        if not rel:
            return None
        cw_path = courseware_root / rel
        if not cw_path.exists():
            raise CoursePackError(
                f"课程 '{course_id}' 声明的课件不存在: courseware/{rel}"
            )
        fm = _read_frontmatter(cw_path)
        declared_course = fm.get("course_id")
        if declared_course and declared_course != course_id:
            raise CoursePackError(
                f"课件 '{rel}' 的 course_id='{declared_course}' 与课程 '{course_id}' 不一致"
            )
        attachments: list[Attachment] = []
        for a in fm.get("attachments", []) or []:
            apath = a.get("path")
            if not apath:
                continue
            if not (materials_root / apath).exists():
                raise CoursePackError(
                    f"课件 '{rel}' 的附件不存在: materials/{apath}"
                )
            attachments.append(
                Attachment(kind=a.get("kind", "other"), path=apath, title=a.get("title", ""))
            )
        return Courseware(
            path=rel,
            title=fm.get("title", ""),
            version=str(fm.get("version", "v1")),
            attachments=attachments,
        )

    def _verify_materials_exist(
        self, course_id: str, materials: CourseMaterials, materials_root: Path
    ) -> None:
        """校验声明的资料路径真实存在,避免 manifest 与磁盘漂移。"""
        paths: list[str] = []
        if materials.lecture_note:
            paths.append(materials.lecture_note)
        paths.extend(materials.slides)
        if materials.code_examples:
            paths.append(materials.code_examples)
        for rel in paths:
            if not (materials_root / rel).exists():
                raise CoursePackError(
                    f"课程 '{course_id}' 声明的资料不存在: materials/{rel}"
                )

    def _parse_capstone(self, raw: dict | None) -> Capstone | None:
        if not raw:
            return None
        milestones = [
            Milestone(
                id=m["id"],
                name=m.get("name", m["id"]),
                deliverable=m.get("deliverable", ""),
                hint=m.get("hint", ""),
                sample_report=m.get("sample_report", ""),
            )
            for m in raw.get("milestones", [])
        ]
        return Capstone(
            name=raw.get("name", ""),
            milestones=milestones,
            overview=raw.get("overview", ""),
            background=raw.get("background", ""),
            final_deliverable=raw.get("final_deliverable", ""),
        )

    def _parse_taxonomy(self, raw: dict) -> Taxonomy:
        if not raw:
            return Taxonomy()
        topics = [
            Topic(id=t["id"], name=t.get("name", t["id"]), course_id=t.get("course_id", ""))
            for t in raw.get("topics", [])
        ]
        return Taxonomy(
            status=ArtifactStatus(raw.get("status", "candidate")),
            topics=topics,
        )

    def _parse_rubric(self, raw: dict) -> Rubric:
        if not raw:
            return Rubric()
        default_dims = [
            RubricDimension(key=d["key"], name=d.get("name", d["key"]), weight=d.get("weight", 0.0))
            for d in (raw.get("default", {}) or {}).get("dimensions", [])
        ]
        default_keys = {d.key for d in default_dims}
        by_course: dict[str, CourseRubric] = {}
        for cid, spec in (raw.get("by_course", {}) or {}).items():
            spec = spec or {}
            dims = [k for k in (spec.get("dimensions", []) or [])]
            # 校验:引用的默认维度 key 必须存在,避免散文/拼写错误静默失效
            for k in dims:
                if k not in default_keys:
                    raise CoursePackError(
                        f"rubric by_course '{cid}' 引用了未知维度 '{k}'(不在 default.dimensions 中)"
                    )
            extra = [
                RubricDimension(
                    key=d["key"], name=d.get("name", d["key"]), weight=d.get("weight", 0.0)
                )
                for d in (spec.get("extra_dimensions", []) or [])
            ]
            by_course[cid] = CourseRubric(dimensions=dims, extra_dimensions=extra)
        return Rubric(
            status=ArtifactStatus(raw.get("status", "candidate")),
            default_dimensions=default_dims,
            by_course=by_course,
        )

    def _parse_questions(self, questions_dir: Path, taxonomy: Taxonomy) -> QuestionSet:
        """解析 questions/*.yaml 预置题库(可选)。

        每个文件形如:
          status: ready
          questions:
            - id: <可选 slug>
              topic_id: <必须存在于 taxonomy>
              difficulty: easy|medium|hard  # 缺省 medium
              prompt: ...
              reference_answer: ...
        目录缺失 → 空题库(向后兼容)。topic_id 非法 → fail fast。
        """
        if not questions_dir.exists() or not questions_dir.is_dir():
            return QuestionSet()
        valid_topics = {t.id for t in taxonomy.topics}
        status = ArtifactStatus.CANDIDATE
        questions: list[Question] = []
        for path in sorted(questions_dir.glob("*.yaml")):
            raw = _load_yaml(path)
            if not raw:
                continue
            # 任一文件声明 approved 即整体沉淀为 approved
            file_status = ArtifactStatus(raw.get("status", "candidate"))
            for item in raw.get("questions", []) or []:
                topic_id = item.get("topic_id", "")
                if topic_id not in valid_topics:
                    raise CoursePackError(
                        f"题库 '{path.name}' 中题目 topic_id='{topic_id}' 不在 taxonomy 内"
                    )
                prompt = str(item.get("prompt", "")).strip()
                if not prompt:
                    raise CoursePackError(f"题库 '{path.name}' 中存在空 prompt 的题目")
                questions.append(
                    Question(
                        id=str(item.get("id", "") or "").strip(),
                        topic_id=topic_id,
                        difficulty=QuestionDifficulty(item.get("difficulty", "medium")),
                        prompt=prompt,
                        reference_answer=str(item.get("reference_answer", "") or "").strip(),
                    )
                )
            if file_status is ArtifactStatus.APPROVED and status is ArtifactStatus.CANDIDATE:
                status = ArtifactStatus.APPROVED
        return QuestionSet(status=status, questions=questions)
