---
name: courseware-authoring
description: >-
  Author and validate CoursewareDoc v1 files for the AI 学习伙伴 course packs — the structured
  Markdown-with-frontmatter format that is the student-facing main body of a course, with raw
  HTML PPT / PDF / code demoted to attachments. Use this whenever a teacher (or agent acting for
  one) needs to convert lecture materials into a courseware file, add a new course's courseware,
  register it in manifest.yaml, choose heading anchors for citation-jump, or fix a courseware
  file the loader rejects. Reach for it even if the user only says "写课件", "转成课件",
  "add courseware", or "the citation jump lands on the wrong section".
license: MIT
---

# Courseware Authoring (CoursewareDoc v1)

Use this skill to turn raw teaching materials (讲义 / PPT / 代码) into a **CoursewareDoc v1**
file: the structured Markdown document that the student app renders as the course's main body.
Raw files become downloadable/previewable **attachments**, not the primary reading surface.

Why the format matters: every `##`+ heading becomes an **addressable anchor**. The student app's
table-of-contents jump and the QA agent's **citation-source jump** both resolve to these anchors.
If you hand-write headings sloppily, citation jumps land on the wrong place. The format makes the
jump target an intrinsic property of the document, not something guessed by counting DOM nodes.

Not for: editing the engine, changing the retrieval pipeline, or authoring the raw PPT/PDF files
themselves (those stay as-is and are linked as attachments).

## Where files live

```
data/course_packs/<pack_id>/
  manifest.yaml            # register courseware: <file>.md per course
  courseware/              # CoursewareDoc v1 files (the main body)
    <course_id>.md
  materials/               # raw source files, become attachments
    lecture_notes/  slides/  code_examples/
```

- Courseware `path` in frontmatter/manifest is **relative to `courseware/`**.
- Attachment `path` is **relative to `materials/`** — the same namespace as citation `source_path`.

## File anatomy

A CoursewareDoc v1 file is YAML frontmatter + Markdown body:

```markdown
---
course_id: langchain_agent          # MUST match the manifest course_id
title: LangChain Agent 基础          # shown as the courseware title
version: v1
attachments:                         # raw files, optional
  - kind: slides                     # slides | pdf | code | other
    path: slides/ppt_01.html         # relative to materials/, must exist
    title: 课堂 PPT
  - kind: code
    path: code_examples/langchain_example
    title: 示例代码
---

# 课程标题（H1，作为开篇，不是可跳转段）

一段导语。

## 这个项目学什么 {#overview}

正文……每个 `##`（及更深）标题就是一个可跳转锚点。

## 核心概念:Agent {#concept-agent}

正文……
```

## Heading & anchor rules (must match the engine)

The anchor for a heading is computed by a slug rule shared between backend
(`apps/api/app/course_pack/slug.py`) and frontend (`apps/web/src/lib/slug.ts`). **Do not
reinvent it.** The rule:

1. lowercase → trim → replace every run of non-`[a-z0-9\u4e00-\u9fff]` with `-` → collapse
   repeats → trim leading/trailing `-`.
2. A trailing `{#custom-anchor}` on the heading **overrides** the computed slug and is stripped
   from the displayed title.

Guidance:

- **Add an explicit `{#anchor}` to any heading you cite or link**, e.g.
  `## 核心概念:Agent {#concept-agent}`. Explicit anchors are stable even if you later reword the
  Chinese title, so citation jumps don't rot.
- Anchors must be **unique within a file**. Duplicate slugs make jumps ambiguous.
- Only `##`–`######` become addressable sections. The single `#` H1 is the document title/intro.
- Fenced code blocks are ignored when splitting sections, so `# comment` lines inside ```` ``` ````
  won't be mistaken for headings.
- Keep each section self-contained: it's also the retrieval/chunking unit, so a section that mixes
  three unrelated ideas retrieves worse.

## Converting raw materials → courseware

1. Read the source 讲义 (usually already well-structured Markdown) and PPT text.
2. Restructure into `##` sections, one coherent idea each. Prefer concept-first ordering.
3. Give cited/important sections explicit `{#anchor}`s.
4. Move the original PPT/PDF/code into `attachments:` — do **not** paste their raw dumps into the
   body. Students click through to attachments for the source artifacts.
5. Fill `course_id` to exactly match the manifest, set `title`/`version`.

## Register in manifest.yaml

Add a `courseware:` field to the course (keep `materials:` — those back the attachments and the
no-courseware fallback):

```yaml
courses:
  - course_id: langchain_agent
    name: LangChain Agent 基础
    courseware: langchain_agent.md      # relative to courseware/
    materials:
      lecture_note: lecture_notes/01_langchain_agent_learning_doc.md
      slides:
        - slides/ppt_01_langchain_agent_v3_fixed.html
      code_examples: code_examples/langchain_example
```

## Validation gate (run before claiming done)

The loader fails fast on drift. From `scaffold/apps/api`:

```bash
.venv/bin/python -c "from app.course_pack import CoursePackLoader; \
  c=CoursePackLoader().load('<pack_id>').get_course('<course_id>'); \
  print(c.courseware.title, len(c.courseware.attachments))"
```

Then confirm the sections/anchors the student app will show:

```bash
.venv/bin/python -c "from app.course_pack import CoursePackLoader; \
  from app.routes.courses import _course_summaries; \
  p=CoursePackLoader().load('<pack_id>'); \
  s=[x for x in _course_summaries(p) if x.course_id=='<course_id>'][0]; \
  print([(x.anchor,x.title) for x in s.courseware.sections])"
```

If content changed, rebuild the retrieval index so citations point at the new anchors:

```bash
.venv/bin/python -c "from app.ingestion.pack_service import ingest_course_pack; \
  print(ingest_course_pack('<pack_id>'))"   # needs .env with embedding creds
```

Common loader errors and fixes:

- `课件不存在` — `courseware:` path wrong, or file not under `courseware/`.
- `course_id ... 与课程 ... 不一致` — frontmatter `course_id` ≠ manifest `course_id`.
- `附件不存在` — an `attachments[].path` doesn't exist under `materials/`.

## Checklist

- [ ] File under `courseware/`, frontmatter `course_id` matches manifest.
- [ ] `##`+ headings for every addressable section; cited ones have explicit `{#anchor}`.
- [ ] Anchors unique within the file.
- [ ] Raw PPT/PDF/code listed as `attachments`, not pasted into the body.
- [ ] `courseware:` registered in `manifest.yaml`.
- [ ] Loader validation passes; index rebuilt if content changed.
