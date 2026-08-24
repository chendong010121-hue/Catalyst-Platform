# BREA USER UPLOAD / WEB BOUNDARY — V0.1

> Review Contract §18. Design boundary only — no implementation of Upload or Web.

## USER UPLOAD — 长程设计边界

```text
Potential future path:
Upload → Ephemeral User Corpus → Parse/OCR → Index Namespace → Query
       → Citation to uploaded source

Default:
NOT authoritative organizational corpus
NOT permanent asset
NOT Platform asset
```

**Review 判定：**

```text
当前：not required（PCE 包络证据：无用户上传需求）
架构影响：若有，需 ingest + index namespace + 引用到上传源的 citation 契约；
          这强化了"ingest/index 层"的候选价值（B 方向），但不构成当前必要性证据。
当前 Review 仅保留该边界为设计契约，不实现。
```

## CONTROLLED WEB — 长程设计边界

```text
Potential future path:
LOCAL FIRST → insufficient local evidence → Web discovery
→ source trust / authority review → scrape / normalize
→ temporary supplementary evidence → reasoning / verification
→ LOCAL vs WEB SUPPLEMENT label + URL
```

**Review 判定：**

```text
当前：rejected（E2 规格 §5 scope excluded；E1 PCR scope excluded）
架构影响：未来需要 source-trust 语义、local-vs-web 证据标注、URL 绑定、
          版本/权威冲突处理 —— 这些正是 RegulationUnit/Verification 面
          的长程扩展点（B 方向兼容），但无当前证据触发。
Review 仅定义契约（label + URL + 补充证据边界），不实现。
```

## 边界决策

```text
BREA_USER_UPLOAD_WEB_BOUNDARY
User Upload : NOT AUTHORIZED / NOT IMPLEMENTED；仅保留设计路径与默认语义
Controlled Web : NOT AUTHORIZED / NOT IMPLEMENTED；仅保留设计路径与标签契约
任何下代候选不得因"未来需要"而提前实现 upload/web。
```
