# EXTERNAL MECHANISM SOURCE REGISTER — V0.1

> Review Contract §19. For every materially used external mechanism: repository /
> official source, version/commit/date where available, source file/documentation,
> mechanism learned, assumptions, what is deliberately NOT inherited.
> External framework popularity is NOT architecture evidence. External content is
> research evidence, != Catalyst authority.

## Mechanism families preserved (Contract §19)

### M-01 — Penguin Harness（已固定参考）

```text
repository      : Prism-Shadow/penguin-harness
commit          : 8e4a77d492a0033e45ac799a681216ed703facac
source file     : packages/skills/skills/benchmark-design/SKILL.md (blob 3ed641c47ab2072d3424a6863857ebe7e97459b5)
mechanism learned: capability/evaluation contract → freeze Candidate identity →
                   separate evaluation identity → design/reveal evaluation AFTER freeze →
                   leak check → preserve exact evaluation revision → traceable decision evidence
assumptions     : benchmark designer knows Candidate; eval runtime deterministic;
                   single-maintainer process possible
NOT inherited   : Penguin Agent State / Skill schema / Benchmark directory layout /
                   Scoreboard / evaluator protocol / Runtime / identity model
role in review  : E2-AB 已用该机制（Evaluation Contract 先于冻结）；本 Review 的
                   "freeze before benchmark" 延续同一机制 —— 机制证据，非实现依赖
```

### M-02 — RAGFlow（deep document understanding RAG engine）

```text
repository      : infiniflow/ragflow（开源 RAG 引擎，基于深度文档理解）
version/date    : 2024-2025 活跃（本 Review 仅机制层面引用）
source          : 官方 README / 架构文档（"deep document understanding",
                   chunk-template / knowledge-graph 构建讨论）
mechanism learned:
  - 文档 → 解析/OCR → 深度理解（版面/标题/表格结构）→ chunk + 结构化元数据 → 索引
  - 检索：关键词/全文 + 向量 + 混合 + 重排（引用来源页码）
  - 引用：答案附来源引用（可溯源）
assumptions     : 面向企业级 RAG 服务（需 LLM 生成答案）；文档规模化；多租户；
                   深度理解依赖 LLM/版面模型；嵌入模型
NOT inherited   : RAGFlow 的 LLM 必需性 / 企业服务形态 / chunk-template 图 /
                   其解析器的产品耦合 / 依赖栈
role in review  : 机制证据：ingestion pipeline 与 citation 的工程模式；不构成
                   BREA 需要 LLM/服务化的证据
```

### M-03 — LlamaIndex（data framework）

```text
repository      : run-llama/llama_index
version/date    : v0.9+（ingestion pipeline 引入，2023-2024）；v0.10+
source          : 官方文档（ingestion pipeline / nodes / indices / metadata
                   extraction：docs.llamaindex.ai；llamaindexxx.readthedocs.io）
mechanism learned:
  - 摄取流水线：load → transform（chunk/embedding/metadata 提取）→ cache → index
  - Document → Node 结构：文本节点 + 元数据（metadata extractor）
  - 索引族：vector / summary / tree / keyword 等 —— 多种检索表示
  - 检索：node 检索 + 后处理（rerank / node postprocessors）
assumptions     : 面向 LLM 应用；文档 → nodes → embeddings 是默认路径；
                   元数据提取常由 LLM 完成；依赖向量存储
NOT inherited   : LlamaIndex 的 embedding 默认 / LLM 依赖 / node 目录 schema /
                   vector store 集成 / Python 框架耦合
role in review  : 机制证据：ingest→transform→index 的分层与 metadata 外置是成熟模式；
                   支撑"知识外置 + 索引分离"方向（B-MIN），但非必要性证据
```

### M-04 — Haystack（LLM framework）

```text
repository      : deepset-ai/haystack
version/date    : 2.x（2024-2026 活跃）
source          : 官方文档（docs.haystack.deepset.ai：pipeline / retrievers /
                   hybrid retrievers / metadata filters）
mechanism learned:
  - Pipeline 组件化：document store → retriever（BM25 / dense / hybrid）→ 后处理
  - 混合检索：keyword + dense 组合（如 AzureAISearchHybridRetriever /
                   WeaviateHybridRetriever），metadata filtering 作为一等公民
  - 多步检索：multi-step / query decomposition 支持
assumptions     : 面向 LLM pipeline；检索器常接向量/搜索后端；dense 需要嵌入模型
NOT inherited   : Haystack pipeline 框架 / 特定 retriever 后端 / LLM 默认 /
                   provider 依赖
role in review  : 机制证据：hybrid 检索 + metadata filter 是成熟模式；但 E1 证据显示
                   BREA 当前面 exact+lexical 已够 → hybrid 为 OPTIONAL UPGRADE 而非必须
```

## 机制结论（综合）

```text
1. ingestion→normalize→index→query 分层 是跨框架的成熟工程模式（M-02/03/04）
   → 支撑"知识外置 + 稳定 ingest/index"方向（H-04 候选），但框架存在 ≠ BREA 必要。
2. metadata 外置 + 检索分离 是普遍做法（M-03 nodes/metadata、M-04 metadata filter）
   → 支撑 RegulationUnit 的 metadata/单元化方向（H-07 候选）。
3. 混合检索（keyword+dense）普遍存在（M-04），但 dense 需要嵌入/向量后端，
   E1 证据显示 BREA 当前无需 → dense DEFER（H-05）。
4. 引用/溯源 是 RAG 产品的基本要求（M-02 引用来源）→ 与 BREA OBL-05 一致；
   但 BREA 的 verbatim 断言比"引用页码"更强，不需要 LLM。
5. LLM 在这些框架中是默认组件（M-02/03/04 均面向 LLM 应用）→
   它们的"LLM 必需"是其产品假设，不是 BREA 的架构证据（H-06）。
```

## 本 Review 的外部引用纪律

```text
未 clone / 未执行 / 未安装任何外部框架代码
外部内容 = research evidence，!= Catalyst authority，!= implementation authorization
无任何外部框架成为未声明运行时依赖
```
