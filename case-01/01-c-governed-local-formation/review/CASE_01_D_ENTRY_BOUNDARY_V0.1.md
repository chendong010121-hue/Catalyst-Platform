# CASE 01-D ENTRY BOUNDARY — V0.1（DESIGN BOUNDARY ONLY）

> 01-C 可准备但**不得执行** 01-D（§29）。本文件仅回答入口问题；不实现 admission/binding。

## 1. 存在哪个精确 Agent 候选？

```text
BREA — Building Regulation Evidence Agent · v0.1-candidate
路径 case-01/01-c-governed-local-formation/candidate/brea-v0.1/
确定性、stdlib-only、无模型；FN-01..11 分解；SEAM-01..03；OBL-01..06 形成验证
```

## 2. 哪些义务已形成证明？

OBL-01..OBL-06（evidence/CASE_RESULTS/T-C01..C03 + OBLIGATION_CONFORMANCE）——formation 证明，非生产验收。

## 3. 哪些接缝已实现证明？

SEAM-01/02/03（GOVERNED_SEAM_CONFORMANCE；可测试/可替换边界）。

## 4. 已证明哪些本地 Builder 能力？

最小 Case-scoped Builder（GAP-01/GAP-05 CASE-CLOSED for Case 01）：定义→清洁目标→生成 19 文件→映射/清单/报告；非通用 Builder Platform。

## 5. 哪些平台缺口仍在？

- GAP-02/03/04/06/07：LOCAL ONLY（本地文件满足；机制未建）。
- GAP-08：Runtime 边界看似足够（Provider 后置）。
- GAP-09（Agent→Platform admission/binding）：**01-D 主题**。
- GAP-10（版本/快照/回滚）：01-F 主题。

## 6. Admission / Binding 下一步必须证明什么？

```text
现有 Platform v0.1 公共边界是否足以承载 BREA 的整机义务（非仅 Capability Descriptor 窄路径）
Agent 级 identity/version/owner 表示如何对接
证据/执行证据如何绑定到已接受 Agent 版本
不改 Platform Core / Runtime 的前提下可绑定到哪一层
```

## 7. 尚不可泛化什么？

Builder 机制（Case-scoped）、BREA 契约（Case-local）、语料（未接纳）、接缝（Agent/Domain 所属）、
任何"成功实现→Platform 能力"的推断。

## 8. 遗留哪些 Case 特定依赖？

语料本地路径（清单解析）、OCR 语料质量、`python -m brea.runner` 良性 RuntimeWarning、本地命令环境（Python 3.12）。

## 9. 组织采纳还缺什么证据？

```text
专业行为评估（01-E）· 运行/执行证据 · Capability 资产化证据 · 用户/组织验收决策 ·
长期语料接纳决策（F-08 未来长期接纳）
```
