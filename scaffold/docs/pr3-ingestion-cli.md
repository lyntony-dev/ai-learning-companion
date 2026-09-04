# PR 3：课程材料 Ingestion CLI 骨架

## 范围

PR 3 增加本地课程材料导入骨架，支持：

1. `validate`：校验课程目录、manifest 与材料文件。
2. `import`：写入 SQLite 的 course/chunk 元数据。
3. `import --rebuild`：清空已有 course/chunk 元数据后重建。

## 课程目录约定

```text
data/course_materials/
  <course_id>/
    course.json
    slides/
      slide_01.md
```

`course.json` 示例：

```json
{
  "course_id": "ppt2_langgraph",
  "course_name": "PPT2：LangGraph 与多 Agent",
  "version": "v1",
  "tags": ["LangGraph", "Agent"]
}
```

## CLI 示例

```bash
make ingest-validate
make ingest-import
make ingest-rebuild
```

或直接执行：

```bash
PYTHONPATH=apps/api python3 -m app.ingestion.cli validate --materials-dir data/course_materials
PYTHONPATH=apps/api python3 -m app.ingestion.cli import --materials-dir data/course_materials --database-url sqlite:///data/app.sqlite
```

## 当前限制

- PR 3 只做确定性单文档单 chunk 骨架。
- 不做 token-aware chunking。
- 不计算 embedding。
- 不写 Chroma。
- 只保存 `text_preview`，不保存完整课程材料正文。
