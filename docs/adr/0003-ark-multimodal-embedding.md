# ADR-0003：Embedding 走 Ark 多模态 `/embeddings/multimodal` 接口

- 状态：已接受
- 日期：2026-07-16

## 背景

离线索引与检索需要文本 embedding。项目使用火山方舟(Ark)的 embedding endpoint（`.env` 中 `EMBEDDING_MODEL=ep-20260714205846-9ktww`，对应模型 `doubao-embedding-vision-251215`）。

实测该模型是**多模态 embedding 模型**：调用 OpenAI 兼容的标准 `POST /embeddings`（body 传 `input: ["text..."]`）会失败；必须调用 `POST /embeddings/multimodal`，且 `input` 为结构化数组 `[{"type": "text", "text": "..."}]`。已验证多模态接口返回真实向量。

## 决策

- Embedding 客户端调用 Ark 的 `/embeddings/multimodal` 接口，而非标准 `/embeddings`。
- 文本输入统一包装为 `[{"type": "text", "text": <chunk>}]`。
- `.env` 用 `EMBEDDING_PROVIDER=ark_multimodal` 标记，embedding 客户端据此选择多模态请求形态。
- 保留"未来接入图片(PPT 截图/图表) embedding"的扩展位：该模型本身支持图片输入，V2 做 VLM/图片解析时可复用同一多模态接口，input 追加 `{"type": "image_url", ...}`。

## 权衡

- **成本**：请求体与标准 OpenAI embedding 不同，需自定义客户端而非直接用 `langchain_openai` 的默认 embedding 封装；维度/批量约束需以多模态接口实测为准。
- **收益**：用对接口，索引链路真实可跑；且天然为 V2 多模态(图片)索引铺路，无需换模型。
- **被否决的方案**：换一个纯文本 embedding 模型。否决理由：当前提供的 endpoint 即此多模态模型，且它对 V2 图片索引有复用价值。

## 影响

- 索引侧 embedding 客户端需自定义 `/embeddings/multimodal` 调用与 input 包装。
- Chroma 向量维度以多模态接口实际返回为准，建库前需固定。
