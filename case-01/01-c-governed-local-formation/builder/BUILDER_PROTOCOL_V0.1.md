# BUILDER PROTOCOL — V0.1 (CASE 01-C / TRACK B · GAP-01/GAP-05 case closure)

> Minimum Case-scoped Governed Builder. **不是通用 Builder Platform。** 架构来自已接受定义，Builder 不发明架构（BC-02）。

## 1. Inputs（逻辑输入）

```text
governed_definition   BUILDER_CONSUMABLE_DEFINITION_V0.1.md（已接受，SHA 6c6e4707…，只读）
request               BUILDER_REQUEST_V0.1.json（candidate_id/version/target/function/seam/obligation/allowed assets/corpus manifest）
```

## 2. Clean-Target Rule（§14）

- 目标目录 `candidate/brea-v0.1/` 必须为空或不存在；非空 → 拒绝并停止（不自动删除任何文件）。
- 生成文件列表 + SHA 记录于 `BUILDER_OUTPUT_MANIFEST_V0.1.json`。

## 3. Generation

- 源：`builder/templates/**`（Builder 拥有的实现 HOW 模板，私有实现自由）。
- 目标：`candidate/brea-v0.1/**`（函数/接缝/义务按已接受定义落位；模板不引入新架构）。
- 生成后 import 冒烟校验（加载 `brea` 包）。

## 4. Outputs（逻辑输出）

```text
generated Candidate workspace
function mapping（FN-01..11）
obligation → test mapping（OBL-01..06）
governed-seam mapping（SEAM-01..03）
private-implementation declaration
generated artifact manifest
build report
build evidence
```

## 5. Defect Classes（§14）

```text
MECHANICAL        记录；修复生成文件；更新报告
INTERPRETATION    记录；修复模板；更新报告
ARCHITECTURE      → STOP（不得自行改架构）
ENVIRONMENT       记录；环境相关；不影响定义
```

## 6. Boundaries

- 只写 `case-01/01-c-governed-local-formation/**`；不写 Catalyst 根/Platform/Runtime；不复制语料（BC-07/BC-08）。
- 不改已接受定义（BC-01）；不生成通用 Platform API。
