# CASE 01 Harness Trial 01 — Knowledge Revision Hash Hardening

## Trial identity

- Authorization commit: `093d6ec2214a98096dbfaf55fa4f1571b97d92bf`
- Frozen executor implementation: `2c2fc065d713b4060d3d6ba7200393a1e83e90a6`
- Trial branch: `case-01-harness-trial-01`
- Target workspace: `E:\w\c01t01`
- Provider/model: `DeepSeekModelProvider` / `deepseek-v4-flash`
- Credential source: `USER_LOCAL` for `deepseek.default`

## KNOWLEDGE_HASH_HARDENING_PROOF

PASS. The governance-owned verifier ran with exit code 0 and 11 tests passed. H-01 through H-11 are PASS. The candidate changes only `knowledge.py`, replacing raw JSON-byte identity with deterministic canonical Knowledge Revision SHA identity. The canonical projection excludes only `sources[].local_reference`; knowledge-bearing values remain identity inputs. Malformed JSON, identity mismatch, non-standard numeric values, and expected-hash mismatch fail closed. Independent source-content SHA verification remains protected.

The representative professional regression is PASS: T-C01, T-C02, and T-C03 remain PASS, and the verifier's H-11 representative v0.8 behavior regression passed. No professional behavior expansion was introduced.

## HARNESS_PRACTICAL_USE_PROOF

PASS. The frozen external executor ran against a separate target worktree. Preflight was READY, credential source was USER_LOCAL, the fresh proof process had no `DEEPSEEK_API_KEY`, and the real `DeepSeekModelProvider` completed the task. The model read only the five authorized repository-relative files and wrote only the authorized `knowledge.py`. Approval allowed that declared write and the fixed `verify-case01-hash-hardening` command. The verification subprocess environment did not contain the provider credential. `governance_authority` remained false. Model attempts were 6 and repair cycles were 0.

The initial bounded invocation exposed two prompt-boundary issues—an abbreviated read path and a multi-call response—and no product file was written by those attempts. The final bounded invocation explicitly represented the authorized paths and required sequential single-tool turns; no Harness implementation, policy widening, or product scope expansion was used.

## Integrated Trial governance

Before evidence creation, the persistent product diff relative to the authorization commit contained exactly one file: the authorized `candidate/brea-v0.8/brea/knowledge.py`. KR-001, KR-002, KR-003, `corpus.py`, `runner.py`, `professional.py`, `semantic.py`, `facts.py`, existing v0.8 tests, historical evidence, main, and the original case-01 ref remained unchanged. The frozen executor remained detached at `2c2fc065...` and unchanged.

The two named Trial evidence files are the only post-run governance files created. No credential value, credential-store content, or credential-store path is recorded. This Trial does not claim OS/container/filesystem/network sandboxing, Platform promotion, admission, binding, v0.9, E2 close, or merge authority.

## INTEGRATED TRIAL VERDICT

CASE01_HARNESS_TRIAL_01_PASS
