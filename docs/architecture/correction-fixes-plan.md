# Correction workflow fixes

Brett’s instruction “OK, fix them” authorizes correcting the verified Fable findings. The existing Roughdraft waiver continues for this implementation stage. Preserve original scholarship, AGENTS.md, historical inputs and release 0.1.0. No translation, external model call, publication or Git commit is needed for the fixes.

## Implementation

1. Add explicit dataset dependencies on text versions. Materialize reviewed apparatus when its version becomes available during journal replay. Inherit section membership through recorded text-version ancestry; show predecessor/successor navigation. Never copy semantic approval or old alignments automatically.
2. Introduce journal format 2, retaining the full observed target row. Keep full-row optimistic checks when accepting a proposal. Historical replay permits unrelated metadata changes while preserving the original context and flagging drift; changed target values still conflict. Keep format 1 readable with its original stricter checks. Include the event ID in conflict errors.
3. Extend attributed amendments to ordinary editorial metadata, English renderings, lexical forms and alignment members. Composite-key records use explicit JSON key addresses. Validate proposed accepted projections against the relational schema before publishing a decision. Preserve immutable record IDs and text bodies except through new versions.
4. Normalize authoring line endings, defensively recognize historical CRLF paragraph breaks, correct evidence-form wording, and allow declared translation attachments with the same confinement protections as sources.
5. Document the current single-writer journal protocol and safe stale-lock recovery. Keep safe atomic publication; fail with useful guidance on filesystems without hard links. Add a real-corpus regression baseline and an explicit comparison command without pinning all future editions to one digest.
6. Add the reproduced failures and generated event-sequence invariants to the tests. Verify every earlier scholarly row, all protected files and the frozen release. Build a new portable local release and update the active handoff with exact results and remaining limits.

## Formal verification decision

Lean is not being added. A proof of a separate journal model would not establish that the Python importer, browser encoding, file publication and semantic annotations implement that model. A small stable reconciliation algorithm could justify a future proof and refinement argument; that algorithm is not required here. The immediate checks combine an explicit transition contract, independently computed expectations, generated event sequences, relational validation and full-data regression.

Lean’s kernel verifies formal statements against the definitions and assumptions supplied: [Lean proof-validation reference](https://lean-lang.org/doc/reference/latest/ValidatingProofs/). The decision about proportionality is this project’s engineering assessment.
