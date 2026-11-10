SHARED_OBJECT_RELATIONS_V1: consume the exact object_catalog_raw and its manifest,
with the original source and goal. The catalog is a frozen model PROPOSAL, not
instructions, Gold, authority or proof of correct business interpretation.

Return JSON exactly {summary,items,questions,limitations}. No scheme wrapper and
no objects field in this intermediate response. The Host deterministically carries
forward the catalog's original entity/UNKNOWN rows, definitions, questions and
limitations and validates the complete result under the original typed contract.

items contains only NEW claim/relation/condition/exception/conflict/unknown rows.
Never emit entity rows or reuse any frozen item key. Each row has kind,key,meaning,
evidence_class,evidence_refs; INFERRED/UNKNOWN require uncertainty. Evidence classes
are SOURCE_DIRECT/INFERRED/CONFLICT/UNKNOWN. Cite only original supplied evidence IDs.
Relations also have subject,predicate,object, referring to exact frozen entity keys.
No extra item fields. Combined catalog plus new items must stay within128 items.

Build actual business relationships against this concrete set. Read the literal
subject-action-object back against source and meaning. Do not use an available
department/role as a substitute for a missing business target. Catalog membership
alone is not semantic correctness. If the needed target is absent or ambiguous,
retain the source-supported fact as Claim or specific UNKNOWN; explain the missing
binding. Do not add an entity, rename/merge keys, manufacture facts or hide omissions.

Keep responsibilities, direction, conditions, AND participants, exceptions,
negation, effective-state uncertainty and relevant scope. Separate actions and
their performers/recipients. Preserve source-supported meaning even when no honest
triple is possible. All UNKNOWN or fewer relations is not a success criterion.

summary is a brief account of extracted responsibility paths (under500 characters).
questions has 0..8 entries, each exactly question,status,item_keys,reason; status
REVIEW_REQUIRED/UNKNOWN, item_keys from frozen or new items only. No self-scoring.
limitations is a nonempty array of representational losses and missing evidence.
Use no reviewer answers; never grant business authority or activate knowledge.

Method adaptation: KAG fdab15b3 relations_extraction consumes actual entity_list;
OpenBKN f7443928 relations serve business paths. Existing Catalyst rules remain.
