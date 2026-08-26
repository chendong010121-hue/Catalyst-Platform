# CATALYST PLATFORM V0.1 — EXTERNAL TEST COMPARISON BASELINE

> **Purpose:** compare the same test responsibilities against mature external projects before interpreting Catalyst results.
> **Authority:** external projects are mechanism/evidence donors, not Catalyst architecture authority.
> **Reviewed:** 2026-08-26

## Comparison matrix

| Test responsibility | External project approach | Catalyst V0.1 approach | What we are testing |
|---|---|---|---|
| Choose simplest solution form | Anthropic distinguishes predefined workflows from dynamic agents and recommends adding complexity only when necessary. LangGraph uses the same workflow/agent distinction. | Construction Skill searches Capability value first, then chooses Skill / deterministic implementation / Workflow / Service / Agent / composition. | Catalyst must choose Workflow for fixed paths and Agent only for observation-dependent control. |
| Deterministic component testing | OpenAI Agents SDK provides provider-neutral scripted doubles for SDK-owned orchestration and says provider-owned behavior requires real integration tests/evals. | Catalyst uses deterministic fake/provider seams for Runtime-owned behavior and keeps provider/model quality outside those claims. | No deterministic test may overclaim model/provider behavior. |
| Stateful workflow testing | LangGraph recommends fresh checkpointers for tests, isolated node/partial execution, and uses persistence/checkpoints for resume/fault-tolerance testing. | Catalyst Runtime already owns durable Session / pending execution / reconciliation / cancellation semantics and has deterministic regression for those boundaries. | Integration must not duplicate state/recovery semantics in Harness or Platform. |
| Agent evaluation | Inspect AI separates Task, solver/agent, scorer, sandbox and writes structured evaluation logs. Anthropic also emphasizes task/trial/trajectory/outcome/grader distinctions. | Catalyst keeps Construction responsibility/evidence requirements separate from Evaluation implementation and interprets evidence toward Capability reuse/replace/Harvest. | Construction must not absorb evaluator mechanics; Runtime failure must not become product score failure. |
| Catalog/discovery | Backstage keeps metadata in source control close to code and uses the catalog for discoverability rather than replacing source authority. | Catalyst uses a tiny repository-native Visibility Index with `authority_ref`, optional capability/asset/evidence refs, and no copied contracts/health. | Index must remain navigation, not Registry/DB/source of truth. |
| Tool/context interoperability | MCP distinguishes user-controlled prompts, application-controlled resources and model-controlled tools; tools are protocol primitives with their own schemas. | Catalyst treats MCP as an interoperability mechanism/adapter surface. A tool is not automatically an organizational Capability. | External MCP intake must not mint a Catalyst Capability per tool. |
| Multi-agent selection | LangChain/LangGraph explicitly states not every complex task needs multi-agent; a single agent, Skills, routers or custom workflows may be sufficient. | Catalyst treats named roles as responsibilities, then chooses the simplest form. | Planner/researcher/writer labels must not automatically become three Agents. |
| External Agent harvesting | Waku Case02 provides a real complete external Agent whose retrieval/memory mechanisms were decomposed into governed Case-local assets. | Catalyst Visibility Index exposes `WAKU-A01` without admitting it as a Platform Capability and can reuse the responsibility without local Waku runtime code. | Original Agent form must be disposable while harvested value remains discoverable. |
| Implementation replacement | Inspect tasks/solvers and LangGraph stores/checkpointers expose replaceable interfaces; OpenAI testing replaces owned normalized boundaries with doubles. | Platform public Capability WHAT is stable while Runtime implementation HOW can be replaced if conformance holds. | Alternate `compose_report` implementation must execute under the same id/version contract. |
| Failure attribution | OpenAI separates SDK-owned orchestration tests from provider tests; Inspect separates solver/scorer/sandbox; LangChain separates unit/integration/eval layers. | Catalyst separates Platform contract, Binding/Conformance, Runtime execution certainty, product/evaluation evidence. | Missing capability, incompatible binding, unresolved Runtime and wrong product output must have different owners. |

## Official references reviewed

- Anthropic — Building Effective Agents: https://www.anthropic.com/engineering/building-effective-agents
- Anthropic — Demystifying evals for AI agents: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- OpenAI Agents SDK — Testing: https://openai.github.io/openai-agents-python/testing/
- LangGraph — Workflows and agents: https://docs.langchain.com/oss/python/langgraph/workflows-agents
- LangGraph — Test: https://docs.langchain.com/oss/python/langgraph/test
- LangGraph — Persistence: https://docs.langchain.com/oss/python/langgraph/persistence
- LangChain — Multi-agent: https://docs.langchain.com/oss/python/langchain/multi-agent/index
- Inspect AI — Tasks: https://inspect.aisi.org.uk/tasks.html
- Inspect AI — Scoring: https://inspect.aisi.org.uk/scoring.html
- Inspect AI — Eval Logs: https://inspect.aisi.org.uk/eval-logs.html
- Backstage — Software Catalog: https://backstage.io/docs/features/software-catalog/
- MCP — Server primitives: https://modelcontextprotocol.io/specification/2025-06-18/index

## Interpretation rule

External similarity is not a PASS by itself.

A Catalyst test passes only when:

```text
the same responsibility is satisfied
+ Catalyst ownership boundaries remain intact
+ no unnecessary abstraction was added
+ the result is replaceable
+ the evidence does not overclaim what was tested
```
