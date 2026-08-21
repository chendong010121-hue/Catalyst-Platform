# PRODUCT INTENT REQUIREMENT MATRIX — V0.1（BLIND · D0 · U-2）

> 每条意图要求：requirement_id / statement / evidence_refs[] / confidence / source_type / implementation_status。
> 置信类：PROVEN / STRONGLY SUPPORTED / WEAKLY SUPPORTED / UNKNOWN。实现状态见 OBSERVED_CAPABILITY_MATRIX。

| REQ | statement（盲恢复） | evidence_refs | confidence | source_type | implementation_status |
|---|---|---|---|---|---|
| REQ-L01 | 单问题规范咨询：问题+项目条件→本地规范检索→适用性判断→自然回答，结论可展开来源 | design spec §2.1.1; AGENTS.md | STRONGLY SUPPORTED | design doc | INTENDED_NOT_IMPLEMENTED（2.0 代码无检索/回答链） |
| REQ-L02 | 项目文件夹自动分析：解析规划条件资料→提取事实→用户确认锁定→关注事项/风险/缺失 | design spec §2.1.2; AGENTS.md; phase-2-report | STRONGLY SUPPORTED | design doc + report | PARTIAL（摄入/事实已实现；分析未实现） |
| REQ-L03 | 文档来源保真：原文件只读、SHA 指纹、来源坐标、OCR 置信 | documents/_source.py; domain/documents.py; phase-2-report | PROVEN | code + report | IMPLEMENTED |
| REQ-L04 | 事实提取与用户确认：候选→修订→确认（不可变）；已确认事实保护 | domain/facts.py; facts/ledger.py; AGENTS.md | PROVEN | code + tests | IMPLEMENTED |
| REQ-L05 | 正式/候选证据边界：候选不得自动提升为正式证据/引用/确定性结论 | AGENTS.md; prompt-charter-audit.md | STRONGLY SUPPORTED | policy doc | PARTIAL（provenance 实现；证据治理在 legacy1） |
| REQ-L06 | 引用可追溯：真实来源+块标识，不创建不存在引用 | AGENTS.md; prompt-charter-audit.md | STRONGLY SUPPORTED | policy doc | PARTIAL |
| REQ-L07 | 三分离判断：正式来源身份≠语义适用性≠覆盖充分性 | design spec §1-7; prompt-charter-audit.md | STRONGLY SUPPORTED | design doc | INTENDED_NOT_IMPLEMENTED（2.0） |
| REQ-L08 | 本地规范优先 + 网络策略：仅本地缺口或用户验证请求才触发网络；网络材料候选化 | AGENTS.md; config.py network_mode | STRONGLY SUPPORTED | policy + config | INTENDED_NOT_IMPLEMENTED（network_mode 无消费点） |
| REQ-L09 | 规范理解/适用性/证据绑定（normative reasoning & binding） | design spec §5.1; AGENTS.md | STRONGLY SUPPORTED | design doc | INTENDED_NOT_IMPLEMENTED（2.0） |
| REQ-L10 | AnswerDocument 单一答案源 + DOCX/PDF 导出 | AGENTS.md; design spec §2.2/§4.3 | STRONGLY SUPPORTED | policy + design | INTENDED_NOT_IMPLEMENTED（2.0） |
| REQ-L11 | provider 双支持：Codex + OpenAI-compatible | design spec §2.2; config.py provider_kind; providers/codex.py | PROVEN（codex）/ WEAKLY（openai_compatible 仅声明） | code + config | PARTIAL |
| REQ-L12 | 项目/上下文隔离（project_id 归属一切业务数据） | domain/projects.py; storage/schema.py; phase-2-report | PROVEN | code + report | IMPLEMENTED |
| REQ-L13 | 运行/审计状态：run + append-only events | domain/runs.py; storage/schema.py | PROVEN | code | IMPLEMENTED |
| REQ-L14 | 扫描 PDF/OCR 支持（rapidocr） | documents/ocr.py; pyproject.toml | PROVEN | code + manifest | IMPLEMENTED |
| REQ-L15 | 评价/验收：60 题 golden corpus（VG/L/N），三层比较，阻断错误门禁 | docs/migration/golden-corpus-audit.md | STRONGLY SUPPORTED | audit doc | INTENDED_NOT_IMPLEMENTED（语料冻结待裁决；评价未实现） |
| REQ-L16 | 可打包交付：PyInstaller 构建 + Windows 一键启动脚本 | pyproject.toml（build extra）; scripts/*.ps1 | STRONGLY SUPPORTED | manifest + scripts | PARTIAL（脚本/构建声明存在；打包产物未见） |

（注：以上为盲恢复意图；对比阶段将与 01-A/B/C 已知证据核对——`BLIND_VS_*_COMPARISON`。）
