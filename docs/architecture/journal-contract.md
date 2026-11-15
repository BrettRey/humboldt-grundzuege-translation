# Journal invariants and verification

The authority consists of immutable base bundles, explicitly dependent apparatus datasets, and attributed proposal/decision events. New events use format 2; format 1 remains readable with its original strict preconditions. All text body changes create new version IDs. Ordinary metadata changes project over preserved base values and retain their before/after history.

## Transition contract

- A proposal records a permanent target address, changed field, old/new values, full target fingerprint and complete observed row. Its snapshot must match its fingerprint and original value.
- Saving or accepting a pending proposal requires a matching current whole row. Metadata changes cannot silently make a stale proposal acceptable. Rejection can still be recorded explicitly.
- During historical replay, format 2 permits unrelated base-context changes while recording the original context and review impacts. Changing the target’s original value remains an error. Changes caused by intervening journal events are checked against the context at proposal registration and cannot be smuggled into an acceptance.
- A rejected proposal makes no change to scholarly content. A successful accepted amendment preserves the original value in base data/history. Text edits preserve every older body and its units/links.
- No old alignment, evidence status or semantic approval is transferred automatically. Exact-string reattachment candidates are observations for review. New apparatus is declared explicitly and becomes available when all `requires_versions` dependencies exist.
- Dependent apparatus is materialized during replay, so later proposals can target its records. A missing dependency, invalid span or relational failure rejects the import. Accepted changes are relationally preflighted before their decision event is published.
- Rebuilding the same inputs has the same logical content regardless of physical record order. SQLite file layout, build metadata and migration application times are outside that logical identity.

The journal has one authoritative writer. Clones exchange fingerprinted proposal drafts, not independently numbered journal branches. Publication uses exclusive atomic file creation; it does not silently replace an event. Abandoned locks require human inspection. These are operational constraints, not authenticated authorship or distributed consensus.

## Evidence for the contract

Regression workflows cover the concrete Fable failures, browser-form handling at the HTTP boundary, dependent apparatus, metadata history, composite-key records, invalid acceptance and release comparisons. Generated tests compare 40 deterministic sequences of 30 operations with an independent small editorial state model, including stale acceptance and explicit rejection. Further generated text revisions check preservation of all older bodies and semantic links. These checks are executable evidence, not a mathematical proof.

The default suite also reconstructs the real initial scholarly corpus against `edition/baselines/initial.json`; no source PDFs or historical databases are required. Explicit release comparison checks later complete editions without treating one initial digest as an eternal content restriction. SQL and JSON column contracts are checked against one another.

## Role of a proof assistant

Adding Lean now would have low value relative to its cost. A theorem about a separate abstract journal would leave the importer, Python implementation, Unicode offsets, browser encoding, SQLite and file operations outside the result unless a refinement argument connected them. The defects that motivated this work were mainly at those boundaries.

A proof could become useful for a small stable reconciliation algorithm, especially if multiple authoritative writers become necessary. Its theorem would need an explicit specification, assumptions and connection to executable code. It would still say nothing about whether the German reading or English interpretation is correct. Lean verifies formal statements against supplied definitions and assumptions: [Lean proof-validation reference](https://lean-lang.org/doc/reference/latest/ValidatingProofs/). No Lean dependency, proof skeleton or external proving job has been added.
