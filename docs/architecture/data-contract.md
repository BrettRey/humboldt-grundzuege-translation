# Data and computation contract

## Authority and generation

`edition/manifest.json` names and hashes the durable datasets. Four initial bundles preserve the existing scholarly database: text/layout records, evidence/decisions, terminology, and the §147 passage. Canonical record IDs are explicit immutable identities. Old list-derived names are retained as fixed legacy identifiers; new code never recomputes sense identity from list order. Derived word IDs are scoped to immutable text versions.

The database and reading views are projections of those datasets plus the append-only proposal/decision journal. They are not the authoritative editing surface. Original sources and historical model-run artifacts remain separately preserved; rebuilding the edition never invokes a model, a historical builder or an ignored database. The one-time `tools/migrate_legacy_snapshot.py` is migration evidence, not a normal dependency.

## Generic passage apparatus

A passage declares its logical section and versions. Layouts specify stable paragraph and segment IDs and exact source-sentence/rendering block text. Shared code generates written-token units using `unicode_lmn_v1`: Unicode letters/marks/numbers, retaining internal hyphens and apostrophes. It does not claim linguistic segmentation. Explicit annotation records can overlap and many-to-many alignments can connect multiple units on either side.

The initial canonical export stores deterministic word recipes instead of thousands of copied derived word rows. The importer verifies their expected counts and reconstructs the exact original spans, IDs, labels and discovery metadata. All 33 pre-existing scholarly tables were compared row-for-row after the first reconstruction; provenance records store counts and logical table hashes.

## Versions and change

Record schemas and SQL schemas have distinct versions. SQL migrations are bundled with the engine and checked against their history; they evolve storage without licensing a change of meaning. Canonical input hashes, body hashes, parent/span checks, foreign keys and exact anchoring apply at build time. `input_digest` identifies the manifest and journal; `logical_digest` identifies durable logical table content independent of build time, path and SQLite file layout.

Accepted interpretation changes preserve before/after values and attributed decisions. Text revisions create new versions and proposed analyses, with explicit reattachment/impact records. Old alignments remain attached to their original versions. The engine does not infer that a copied span carries the same meaning after revision. The local reader can inspect old and current records and download fingerprinted proposals; importing or accepting one is a separate authoring action.

Journal format 2 retains the complete observed target row. Full-row checks protect pending acceptance; historical replay distinguishes later base-context drift from conflicting journal transitions, preserves the original context and flags review impacts. Format 1 remains readable under its original strict rules. Explicit composite JSON addresses identify renderings, forms and alignment members. Metadata amendments do not overwrite base files; a form/headword amendment also updates its derived search key.

Apparatus bundles may declare `requires_versions`. They materialize during replay when their referenced versions exist, before subsequent amendments targeting that apparatus. Logical passage membership follows explicit text-version ancestry; verification status and old semantic links do not. The [journal contract](journal-contract.md) states the transition invariants and testing limits.

## Publication and recovery

Builds publish a complete, validated database atomically; normal fresh outputs cannot overwrite another file. Authoring serializes cooperating writers with a project lock and publishes one immutable event per file. Imports validate before switching the manifest. An interruption may leave an unreferenced candidate file or lock for inspection, not an intentionally half-validated active manifest. File and directory syncing improves crash durability on supporting filesystems; filesystem guarantees remain relevant.

One authoritative project copy writes the journal; other contributors exchange drafts. Independent journal branches cannot be merged by copying/renumbering files. Atomic authoring requires hard links; FAT/exFAT support is limited to reading copied material. Only a confirmed abandoned lock may be removed after inspecting its recorded owner and running commands.

Optional source attachments are declared resources. Their absence is reported, while embedded transcriptions/quotations retain their recorded verification level. The preserved 1906 provisional-base policy, uncertain source readings and lack of specialist validation remain visible in the actual data.

Generated `build/` and local `releases/` are excluded from Git. Source code, schema resources, durable edition records, tests and maintained documentation are the material intended for version control. D014 supplies the commit/publication instruction and explicitly approves the reviewed workflow archives; the handoff records actual publication status. Scoped license grants do not relicense third-party quotations or source publications.
