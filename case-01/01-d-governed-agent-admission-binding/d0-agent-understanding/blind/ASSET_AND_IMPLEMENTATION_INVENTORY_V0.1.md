# ASSET & IMPLEMENTATION INVENTORY — V0.1（BLIND · D0）

> Legacy 2.0 工作区资产/实现清单（盲扫）。不迁移、不评估可复用性（对照阶段再做）。

## 代码（src/standards_agent）

- agent/charter.py（版本化产品 Charter，从 prompt-charter-audit 读取保留策略）
- api/{documents,facts,projects,errors}.py（FastAPI 资源 + ErrorEnvelope）
- config.py（RuntimeSettings：product_root 作用域、provider_kind、network_mode）
- documents/{batches,ocr,pdf,docx,text,_source}.py（摄入/保真/解析）
- domain/{documents,facts,ids,projects,runs}.py（类型化不可变模型）
- facts/{extractor,ledger,normalizer}.py（提取/修订生命周期）
- providers/{base,codex}.py（执行边界；仅 codex 实现）
- services/projects.py；storage/{database,migrations,repositories,schema}.py（SQLite schema v8 + 触发器）；main.py（FastAPI 组装）

## 文档/设计

- README.md；AGENTS.md（交付规则）
- docs/migration/{phase-0,1,2-report}.md；prompt-charter-audit.md；source-assets.yaml；golden-corpus-audit.md
- docs/superpowers/specs/2026-08-14-...delivery-grade-migration-design.md（1103 行产品/系统设计规格）；plans/...implementation.md
- .superpowers/sdd/*（任务简报/报告/评审）

## 测试

- tests/unit（config/charter/documents/facts/providers/services/storage/migration-manifest）
- tests/integration（health/projects/document-batch/fact-confirmation/launcher）
- frontend/tests + frontend/e2e（Playwright；test-results/.last-run.json=passed）

## 配置/依赖

- pyproject.toml（standards-agent-2 2.0.0.dev0；fastapi/uvicorn/pydantic/PyMuPDF/pypdf/rapidocr_onnxruntime/python-docx/reportlab/openpyxl/PyYAML；test/build extras）
- requirements.lock（45 包 Windows 锁）；package.json/package-lock.json（前端）
- .env.example（STANDARDS_AGENT_PROVIDER、STANDARDS_AGENT_LOG_LEVEL——仅名称）

## 脚本

- scripts/{start,stop,standards-agent-runtime}.ps1 + verify-codex-runtime.ps1；tools/verify_migration_manifest.py

## 运行态（观察）

- runtime/test.sqlite（空夹具：projects/analysis_runs/run_events 3 表 0 行）；真实库 agent.sqlite3 未生成；knowledge/ 目录不存在
- 无 data/ 语料目录（语料在 legacy1：data/ocr 2 篇 OCR、51 PDF、index.sqlite、wiki.sqlite、knowledge_snapshot——跨工作区依赖）

## Git 历史（工作区内）

- branch `agent2-delivery`；提交史以 fact recovery/grounding 修复为主（abbcaf1 等 20+ 提交）——事实提取收敛过程证据

## 环境（仅名称）

- CODEX_HOME / CODEX_THREAD_ID / CODEX_SESSION_ID / OPENAI_CODEX_THREAD_ID（providers/codex.py 引用）；STANDARDS_AGENT_PROVIDER / STANDARDS_AGENT_LOG_LEVEL（.env.example）
