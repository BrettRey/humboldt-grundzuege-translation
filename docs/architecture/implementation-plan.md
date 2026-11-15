# Portable edition infrastructure

Brett’s “make it so” authorizes the concrete architecture described in the preceding reply: one Python package, explicit versioned schemas, durable edition records, a generic importer, reproducible SQLite builds, useful reader queries and recorded revisions. The existing Roughdraft waiver and this direct approval allow implementation without another generic proceed checkpoint. Preserve AGENTS.md, all original sources, existing translations, sealed terminology inputs and historical database snapshots. No new translation, publication, remote push, acquisition or spending is part of this task.

## Implementation

1. Export the existing cumulative snapshot once into explicit, durable record bundles. Preserve existing identifiers permanently rather than regenerating them from list position. Regenerate written-token units from their immutable text versions; retain their exact historical identities and spans. Convert §147 to a generic passage dataset consumed by shared code.
2. Introduce `src/humboldt`, a zero-runtime-dependency CLI, numbered SQL migrations and documented JSON record schemas. Normal builds read only declared edition inputs and change records, never historical builders, raw model sessions or ignored databases. Original source attachments are separately verifiable resources rather than prerequisites to querying embedded checked texts.
3. Add combined German/English search, full word/span/term/decision/alternative tracing and a local reader. Keep authoring operations explicit and attributable. Versioned proposals and decisions preserve old readings and report affected links.
4. Test a clean portable copy, a fixture passage addition without new Python, accepted/rejected/conflicting changes, stable IDs, old-version access, schema upgrades, and deterministic logical exports. Compare every legacy row and protected-file hash before and after migration.
5. Produce a frozen local release with data, schema/code versions, hashes and a portable reader; update current documentation while retaining dated historical records.

## Acceptance

A new user can validate and rebuild from durable records, search in either language, inspect the source/evidence/alternatives behind an English phrase, propose and record a revision, retrieve the previous reading, and import another passage as data. A clean-copy test must work without `tmp/`, legacy scripts, source PDFs, network access or model credentials. Source absence stays visible and does not upgrade a transcription’s verification status. No specialist validation is implied.
