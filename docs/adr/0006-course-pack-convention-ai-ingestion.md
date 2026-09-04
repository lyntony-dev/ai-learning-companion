# ADR-0006：课程包契约——约定式目录 + AI 提取管线构建约定格式

- 状态：已接受
- 日期：2026-07-16

## 背景

铁律"引擎内禁止课程硬编码"要靠一个统一的课程包契约兑现:引擎加载 `ai_agent` 与未来任意新课走同一接口。课程包对引擎至少暴露:①资料与知识库 ②知识点体系 Taxonomy ③Rubric ④结课项目里程碑序列 ⑤题库。

关键约束(用户补充):课程包的**原始输入是"脏"的**——HTML 格式 PPT + Markdown + PDF。约定格式**不是手写的,而是用 AI 从原始资料提取构建**。

契约形态候选:A 约定式目录(采纳);B 插件式 Python 代码包(过重,讲师改不了,侵蚀引擎边界);C 全存 DB(编辑/版本化/review 不如文件)。

## 决策

**约定式目录 + 两层结构 + AI 提取管线:**

- 课程包 = `data/course_packs/<id>/`,两层:
  - **原始资料层** `materials/`:交付原样的 HTML PPT / `.md` / `.pdf`。
  - **约定格式层**(AI 管线产出):
    - `manifest.yaml`:id / 名称 / 课程列表 / 结课项目里程碑序列。
    - `taxonomy.yaml`:知识点树(**候选**,讲师可修正)。
    - `rubric.yaml`:批改评分标准。
    - `questions/`:题库(**候选**,预置 + LLM 生成 + 讲师审核沉淀)。
    - chunks/向量:入 Chroma。
- **课程包摄取管线 (Course Pack Ingestion)**:离线构建步骤,用 AI/解析器把原始资料转约定格式:
  - HTML PPT 去壳取正文(按页保 slide_no)、Markdown 直取、PDF 抽文本。
  - 分块产出 chunks(带 course_id / slide_no / section / content_type / source_path / version 元数据)。
  - AI 提取**候选 Taxonomy** 与**候选题库**。
  - MVP 只做**文本层**;图片/图表 VLM 解析为 V2 扩展点(embedding 模型本身多模态,见 ADR-0003,已为此铺路)。
- **候选 → 沉淀飞轮**:AI 产出的 taxonomy/题库标记为候选,讲师审核修正后沉淀。与掌握度"讲师可修正"、好题沉淀同源。
- 引擎侧一个 `CoursePackLoader` 按约定读取,产出统一 `CoursePack` 对象。加新课 = 放新目录 + 跑摄取管线,零改引擎代码。
- `data/raw/` 现有资料按 ADR-0002 迁入 `data/course_packs/ai_agent/materials/`。

## 权衡

- **成本**:需实现摄取管线(HTML/PDF 解析 + AI 提取)与约定 schema 校验;AI 提取质量需讲师审核兜底。
- **收益**:课程包是纯数据、可 git 版本化、讲师可编辑 YAML;引擎零硬编码落地;脏资料到结构化的转换自动化,加课成本低;天然支撑"候选+审核"飞轮。
- **被否决的方案**:B(代码插件,过重且侵蚀引擎边界);C(DB 存储,不利编辑/版本化/review)。

## 影响

- 需新增 `CoursePackLoader` + 约定 schema(manifest/taxonomy/rubric)。
- 需实现摄取管线模块(解析器 + AI 提取 + 分块 + 建库)。
- `data/course_packs/<id>/` 结构写入 DESIGN;`data/raw/` 迁移执行。
- 讲师审核候选产物的接口与教学洞察(T)、题库沉淀同属人机协同飞轮演进线。
