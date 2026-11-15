# Architecture review: Humboldt edition engine

This is a static, single-pass review; nothing was run. I did not consult the advisor tool, because the brief asks for an independent review and excludes extra reviewers.

## Overall assessment

Keep the core shape. Hashed JSON datasets plus an append-only journal are the authority, SQLite is a disposable projection, and the reader cannot write. That is proportionate for one maintainer, has no dependencies, and is candid about what is provisional.

The imbalance is in where the defensive effort went. The storage layer is heavily guarded (migration checksums, sealing, schema comparison) even though the database is rebuilt every time. The correction path, which the stated goal depends on, covers five fields and can strand a corrected text or lock up the build. Nothing here calls for replacement. Most remedies are small and cheapest before the first real journal event; the inventory lists no journal, so I assume none exists yet.

## Strengths

- **Clear authority model.** `input_digest` and `logical_digest` separate "same inputs" from "same content", and release refuses a stale build (`src/humboldt/release.py:46`).
- **Immutable text versions.** Hashed bodies and code-point spans; a text edit creates a new version and never silently re-attaches links (`src/humboldt/revisions.py:453`).
- **Pure, deterministic journal projection.** `apply` does not mutate inputs and is tested for order independence, stale decisions and collisions.
- **Careful reader.** Loopback only, Host check, strict CSP, no JavaScript, escaped output, allowlisted sources; proposals are downloaded drafts.
- **Honest labelling.** Exact versus contextual links are distinguished throughout (`src/humboldt/queries.py:69`), and the docs state the limits plainly.

## Findings

### 1. P1, conditional risk: most corrections bypass history, and nothing is committed
- **Where:** `src/humboldt/revisions.py:26`, `src/humboldt/reader.py:15`, `docs/architecture/data-contract.md:27`.
- **Trigger:** correcting an English term rendering (`sense_rendering`), an alignment, an evidence status, a decision's status or a lexeme form. The journal supports none of these.
- **Consequence:** the only route is hand-editing a 3–6 MB file under `edition/records/` and recomputing its manifest hash by hand. No command does this; only `import` writes the manifest (`src/humboldt/ingest.py:227`). The earlier reading is then gone, because the workspace has no commits and the data contract confirms it is uncommitted.
- **Remedy:** make an initial local commit and one per data edit, so git is the history for base records. This needs Brett's go-ahead, per the data contract. Add journal support for `sense_rendering` when the first such correction arises, not before.

### 2. P2, demonstrated behaviour with a conditional trigger: a row that has ever had a proposal is frozen in every column
- **Where:** `src/humboldt/revisions.py:302`, `src/humboldt/revisions.py:561`, `src/humboldt/revisions.py:250`.
- **Trigger:** editing another column of such a row in the base data. Examples are upgrading `transcription_status` once the critical edition is available, or fixing a sense `label`.
- **Consequence:** replay re-checks each proposal's whole-row hash, whether accepted, rejected or pending. `load` raises a conflict, so `build`, `validate`, `propose` and `decide` all fail. The error names no event, and events cannot be removed because sequences must be contiguous. The only recovery is reverting the edit.
- **Remedy:** on replay, verify only the target field's `old_value`, which is already checked on the same line. Keep the whole-row hash as an authoring-time check in `propose` and `decide`. Add the proposal ID to the error. Do this before the first real event, since it changes what stored hashes mean.

### 3. P2, demonstrated: an accepted text correction cannot be re-segmented and may drop out of its section
- **Where:** `src/humboldt/ingest.py:132` versus `src/humboldt/ingest.py:148`; `src/humboldt/ingest.py:45`, `src/humboldt/ingest.py:104`, `src/humboldt/ingest.py:128`; `src/humboldt/revisions.py:493`; `src/humboldt/queries.py:384`.
- **Trigger:** accepting a one-word fix to an English version.
- **Consequence:** the new version gets only document, paragraph and word units. Sentence units, alignments, evidence and decisions stay on the old version, which is intended.
  - Datasets are expanded and checked before the journal is applied, so a unit or layout naming the new `revision-text-…` ID is rejected. No supported operation can give the corrected text sentence segmentation.
  - Section membership comes from the dataset's declared version IDs or a `§N` in the title. The new version is listed only if its inherited title contains one; the fixture's does not.
- **Remedy:**
  - Document that a correction needing apparatus is entered as a new version in a passage dataset, with layouts and alignments.
  - In `load`, after `apply`, add each new version to its predecessor's passage entry.
  - Show "superseded by" on the old version's page.

### 4. P2, defect by reasoning from browser form rules, not run: reader drafts turn line breaks into CRLF
- **Where:** `src/humboldt/reader.py:207`, `src/humboldt/render.py:188`, `src/humboldt/revisions.py:356`, `src/humboldt/revisions.py:407`.
- **Trigger:** proposing through the browser against any multi-line body, definition, rule or resolution. Browsers submit textarea line breaks as `\r\n`, and the reader passes the value through unchanged.
- **Consequence:**
  - Unchanged text no longer equals the stored value, so the "no change" guard never fires.
  - An accepted body carries CRLF, which shifts offsets.
  - The paragraph splitter does not match `\r\n\r\n`.
  - Old units spanning a line break are reported as missing.
  - The tests post directly with `urlencode`, so they cannot see this.
- **Remedy:** replace `\r\n` with `\n` in `value` and `reason` inside `do_POST`, and add one test that posts CRLF.

### 5. P2, conditional risk: the journal cannot be merged across clones
- **Where:** `src/humboldt/revisions.py:250`, `src/humboldt/revisions.py:315`.
- **Trigger:** two working copies each append event N+1 and are then merged.
- **Consequence:** every journal-reading command fails. Renumbering by hand changes the canonical bytes and the derived source hashes.
- **Remedy:** state in the guide that only the maintainer's copy writes the journal and everyone else sends drafts. The flow at `docs/architecture/user-guide.md:29` already works this way, so nothing needs building.

### 6. P3, demonstrated: contributors cannot attach new evidence, and some declared sources can never be served
- **Where:** `src/humboldt/render.py:188`, `src/humboldt/revisions.py:222`, `src/humboldt/revisions.py:277`, `src/humboldt/ingest.py:218`, `src/humboldt/reader.py:38`.
- **Trigger and consequence:**
  - The form invites "identifiers or objects", but import rejects anything other than existing evidence IDs. A reader with a new citation has no supported path.
  - The reader serves only `sources/`, yet the manifest declares `translations/…` resources. Those display as "not a permitted source attachment" even when present.
- **Remedy:** reword the label to "existing evidence IDs; put new citations in Reason". Either allow `translations/` as a second root or drop those entries from `resources`.

### 7. P3, design preference: storage defences exceed what a rebuilt database needs
- **Where:** `src/humboldt/cli.py:48`, `src/humboldt/ingest.py:191`, `src/humboldt/database.py:229`, `src/humboldt/database.py:378`, `src/humboldt/record_schemas/bundle.schema.json:20`.
- **Observation:**
  - `humboldt migrate` has no input the tool can produce: every build seals, and migrate refuses sealed files.
  - The bundle schema restates the column lists of all 33 tables, which `insert_records` already enforces from the SQL. Any schema change means editing both.
- **Remedy:** leave the working code alone. Drop or hide the `migrate` command. At the next schema change, derive table shapes from the SQL catalogue.

### 8. P3, conditional risk: the default tests never touch the real edition, plus two operational edges
- **Where:** `src/humboldt/cli.py:61`, `docs/architecture/user-guide.md:73`, `src/humboldt/revisions.py:133`, `src/humboldt/ingest.py:195`, `src/humboldt/records.py:64`.
- **Trigger and consequence:**
  - A refactor that alters tokenisation or projection of the real 12 MB data passes the synthetic suite.
  - A crash leaves `.humboldt.lock`, and the error gives no guidance.
  - Publication uses hard links, which fail on exFAT and FAT drives.
- **Remedy:**
  - Record the canonical `logical_digest` in a tracked file and compare it in `validate`.
  - Add "inspect and delete if no command is running" to the lock error.
  - Note the filesystem limit in the guide.

## What would justify revising a major choice

- **JSON bundles as authority:** reconsider only if hand edits to the large files become routine or a second regular editor appears. Even then, split the files per section rather than move the authority into a database.
- **Global journal sequence:** reconsider only if journal files, not drafts, actually arrive from other clones.
- **Inherited 33-table schema:** reconsider when a terminology value stored as JSON text needs field-level revision.

## Highest-priority next steps

1. Commit a baseline, with Brett's go-ahead.
2. Before the first real journal event, apply the remedies for findings 2 and 4.
3. Document the route for text corrections (finding 3) and the single-writer rule (finding 5).
4. Pin the canonical digest (finding 8).

## What static review cannot establish

- Whether the tests pass.
- How long `validate` and `build` take on the real data. Release validation has a 60-second subprocess limit (`src/humboldt/release.py:70`).
- Whether real titles contain `§N` or real bodies contain line breaks. These determine how often findings 3 and 4 bite.
- Whether the journal is actually empty.
- Behaviour across SQLite and Python versions.
- Reader responsiveness when tracing page-sized units.
- Anything about source fidelity or the German scholarship.
