# Frozen inventory method appendix (experimental, explicit opt-in)

The existing Method B remains the ontology design method. The prior inventory is
a source-local mention proposal, not a confirmed ontology or permission grant.
Preserve its raw bytes and manifest identity. No evaluator answers are supplied.

Generate exactly the original {scheme,items} output, not the inventory format.
Every non-rejected mention must have one unchanged entity item and one matching
scheme.objects definition. Do not emit additional entities, silently omit a
mention, canonical-merge identities, or promote pending/inferred to explicit.
Definitions may explain abstraction and business boundaries but may not replace
the exact mention identities/surfaces used by items. Unknown class/instance or
alias identity remains explicit uncertainty, never a forced nearest match.

For each proposed relation, compare the cited clause's actual actor, action and
target to the selected inventory IDs. Co-occurrence in one evidence row is not
support for a particular binding. An organization, its parent, a company, its
branch and its project roles are not interchangeable. A named business object
cannot be silently replaced by its broad domain, generic responsibility or a
nearby department. Missing/inadequate endpoints require a specific UNKNOWN or
claim and limitation, not invented nodes or unjustified positive relations.

Do not emit a relation whose own meaning or limitations say that binding is
unknown. Keep source conditions, AND, exceptions, negation, proposal/effective
status and versions under the existing claim/condition/exception/unknown types.
No extra fields or third fact schema; no operational authority or activation.

After constructing items, form question.item_keys only from actual output item
keys. Question labels, question names and object definitions alone are not item
keys. When no item supports a question, retain UNKNOWN with an empty item_keys
and the precise missing-evidence reason. Never claim it has been answered.

These are producer instructions, not proof of semantic correctness. Existing
typed checks, frozen-inventory checks, independent evaluation and Owner gates
still apply. Do not turn everything into UNKNOWN to hide omitted supported facts.

ADAPT: KAG fdab15b explicit entity-to-relation dependency; OpenBKN f7443928
object definitions and relation boundaries; preserve Method B's EvoOntology
c94389b7 review/authority limits. No upstream runtime code is copied here.
