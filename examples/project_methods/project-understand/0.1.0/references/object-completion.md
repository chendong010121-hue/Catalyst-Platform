# Object-specific responsibility checks

Read only the row relevant to the selected object and the stated target function.

| Object | D0 identification | D1 responsibility | D2 reuse obligations / possible D3 gap |
|---|---|---|---|
| Skill | Frontmatter/body/support files/version/host conventions | Triggers and exclusions, steps, tools/material, outputs, stop; separate prose from scripts | Relative paths, implicit tools, host variables/license/migration loss; host consumption and script effects need observation |
| Agent | Entry/role/model/tools/context declarations | Goal, loop, tool choice, context/state, stop/failure; separate Agent from called framework | Extractable actions/method/state, composition obligations and inseparable dependencies; dynamic routing/cancel/concurrency may need observation |
| Plugin | Manifest/version/entry/declared dependencies | provides/requires, apply/mount, registration/revocation, resources/error cleanup; declaration is not occurrence | Conflicts, injected host services, forced dependencies, unload/effects; duplicate/missing dependency/failure cleanup may need observation |
| Repository/System | Revision/language/layout/license/lock files | Real entry and responsibility chain for target only | Selected cross-module/service/resource boundaries; preserve whole-package reference when needed; configuration/dynamic state may need observation |
| Tool/Workflow | Schema/entry or steps | Per-action or inter-step inputs/outputs/conditions/errors/effects | Type/order/state/permission requirements; do not automatically label a workflow an Agent; compensation/non-idempotence may need observation |

Shared dependencies refer to the same source revision/evidence. An Agent containing
Plugins does not require complete re-analysis of every Plugin. Unsupported languages,
dynamic registrations and missing licenses remain explicit unknowns. Do not convert
source projects into enterprise Entity/Relation/Claim truth records merely to fit a
schema. Handoff is project-understanding.v1, for independent review and later reuse.
