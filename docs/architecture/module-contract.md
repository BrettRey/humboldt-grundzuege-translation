# Shared implementation contract

Modules are standard-library-only under `src/humboldt`; normal builds import no legacy modules. This document records the implemented interfaces; [the user guide](user-guide.md) gives contributor commands.

## Database API (database.py)

- `connect(path=':memory:', *, readonly=False)` returns sqlite3.Row connection with FK enabled.
- `migrate(db, target=None)` uses packaged numbered SQL files and a checksummed `schema_migration` history. Version 1 preserves the 33 existing scholarly tables, view, indexes and triggers. Version 2 adds build metadata, revision history and change impacts. Migration files live in `src/humboldt/migrations/`; top-level `schemas/migrations/` documents the authoritative package path, avoiding duplicate SQL copies.
- `seal(db)` protects every table from ordinary writes after construction. Rebuilds/projected revisions happen on fresh DBs. `report(db)` gives counts, FK and integrity results. `logical_digest(db)` hashes canonical durable rows, excluding build metadata and migration application times. SQLite protections are not a security boundary against a database owner.
- `insert_records(db, tables)` imports explicit table rows; handles unit-parent order and alignment draft/member/freeze ordering. Table allowlist is introspected from version1 schema, never interpolates user SQL identifiers unchecked. Derived word units are supplied by ingest before linked rows.

## Durable inputs (ingest.py)

`edition/manifest.json`: format `humboldt.edition`, schema_version 1, id, datasets[{path,sha256}], optional resources[{path,sha256,required:false}] and reading_defaults[{section,source_id,target_id}]. Dataset paths resolve within edition/. Decision events live in edition/changes/; proposal events in edition/proposals/. Historical migration evidence lives in edition/provenance/ and is not a runtime prerequisite.

Bundles: format `humboldt.records` or `humboldt.passage`, schema_version1, id, tables{table:[row...]}, optional layouts[] and word_recipes[]. Table rows use existing SQL columns and explicit immutable IDs. Layouts generate paragraph, segment and word units from saved text-version bodies. Word recipes generate words from a containing unit, retaining exact ID/label patterns. `ingest.build(project, output, *, changes=True)` writes a fresh atomic DB; `ingest.load(project, *, changes=True)` returns `(tables, metadata)` after input hash/schema validation. `ingest.validate(project, *, sources=False)` performs the full build/record checks without changing authoritative inputs. `ingest.add_dataset(project, source)` validates and copies a bundle, updating the manifest under a shared lock.

Optional `requires_versions[]` delays a bundle until its version dependencies exist. `apply(..., materialize=callback)` invokes the loader’s materializer before replay and after accepted changes, permitting apparatus for new versions and subsequent amendments of that apparatus. Missing dependencies fail. `ingest.verify(project, reference)` compares the immutable manifest in a baseline record or current complete content against an explicit release record.

## Query/reader API (queries.py, reader.py)

Accept an open read-only sqlite connection, never mutate it. `queries.search(db, text, limit=30)` searches German/English terms and texts, returning JSON-serializable results. `queries.trace(db, unit_id)` includes ancestors AND overlapping annotations, decisions, evidence, linked versions/alternatives, term associations, and revision impacts, with exact versus context relations labelled. `queries.entity(db, kind, id)` returns details/history; `queries.passage(db, section)` gives version choices and linked texts.

`reader.serve(project, db_path, host='127.0.0.1', port=0)` runs a loopback browser UI with search, passage and trace inspection and source links confined to declared project resources. Browsing is read-only; forms download fingerprinted proposal drafts. Dataset strings are escaped. Explicit reading defaults choose versions without declaring editorial acceptance.

## Revision API (revisions.py)

`propose(project, *, kind, target_id, field, value, by, reason, evidence=(), expected_sha256=None)` persists an append-only proposal with UUID, full-row target fingerprint, timestamp and attribution. `decide(project, proposal_id, *, accept, by, reason)` records acceptance/rejection under an exclusive project lock. Stale acceptance fails; explicit stale rejection remains possible. Supported fields are text_version/body, term_sense/definition|rule|caution and decision/resolution. `apply(tables, events)` returns projected tables plus revision_history/change_impact rows; `read_events(project)` returns the validated journal. Text changes create a new version and proposed mechanical analysis/units, preserving old bodies and alignments.

The current `SUPPORTED` mapping additionally covers editorial metadata, renderings, lexical forms, evidence descriptions/status and alignment members. `record_key(kind, identifier)` and `record_id(kind, row)` encode/decode allowlisted composite JSON keys. Format 2 proposals include a fingerprinted `target_snapshot`; old format 1 events remain accepted with their original replay checks. Full-row checks remain strict at authoring/acceptance. Historical context drift is recorded; conflicts with intervening journal changes are refused. Decisions are relationally preflighted before publication. Text normalization is confined to authoring values, never old source bodies/spans.

Project writes use shared `project_lock(project)` (exclusive lock file, no automatic stale-lock deletion), canonical JSON and atomic publication. Journal events use exclusive file creation, ordered sequences and exact compact JSON plus a newline. Imports validate the candidate before publishing its manifest. The user guide describes recovery limits and conservative reattachment.
