# Build, inspect and revise the edition

The current engine uses Python 3.11+ and its standard library. No model credentials, database server or package installation is needed. Run commands from the project root; `python3 humboldt` is equivalent to `./humboldt`. An installed package can instead expose the `humboldt` command through `pyproject.toml`.

## Start reading

```bash
./humboldt validate
./humboldt build
./humboldt browse
```

Open the loopback URL printed by `browse`. Choose §1, §2 or §147 and a text version. Click a word or block to inspect its ancestry, overlapping annotations, evidence, translation alternatives and decisions. Labels distinguish exact selected spans from contextual associations; a sentence alignment is not presented as word-for-word equivalence. Search accepts German and English, including saved terminology renderings. The reader makes no database changes.

The manifest’s `reading_defaults` selects the checked source and revised English for each prepared section. Every version remains selectable, labelled with its permanent ID. These are reading defaults, separate from editorial acceptance. To make a later successor the default, update that explicit manifest entry and rebuild.

```bash
./humboldt search understanding
./humboldt passage 147
./humboldt trace 'difficult-147-de-v1:s05:w013'
./humboldt show term_sense 'lex:verstand:s01'
./humboldt status
```

Checked text and evidence are embedded in the database. Original source attachments may be absent in a portable copy; the reader says so. `./humboldt validate --sources` additionally checks hashes of attachments available in this project. Missing originals do not upgrade or invalidate the recorded quotation-check status. The unavailable critical edition and specialist-validation limits remain as before.

## Propose and review a correction

An entity page offers amendment links for text bodies and metadata; terminology labels, definitions, rules, cautions and English renderings; lexical forms; evidence descriptions/status; decision metadata; analysis metadata; and alignment descriptions/members. Supply attribution, reason and existing evidence IDs where applicable, then download the draft. This saves no editorial change. Import it into the working project:

```bash
./humboldt import-proposal /path/to/humboldt-proposal-draft.json
./humboldt history
./humboldt decide PROPOSAL_UUID --accept --by 'Editor name' --reason 'Evidence-based explanation'
./humboldt build --force
```

Use `--reject` for an explicit rejection. The complete target fingerprint must still match at import and acceptance; stale acceptance needs a fresh proposal. Rejection remains recordable after another change. The CLI also supports direct `propose`; see `./humboldt propose --help`. Authoring normalizes CRLF/CR to LF. The immutable original text and its offsets are never normalized in place.

Records with composite keys use a JSON address, for example `./humboldt show sense_rendering '{"sense_id":"lex:verstand:s01","rank":1}'`. The reader constructs these addresses for you. Forms and renderings have their own linked record pages. IDs, source fingerprints and text-version body hashes are not general editable fields. A lexical headword/form amendment updates its derived search key. An acceptance that would break a foreign key, alignment constraint or allowed status fails before a decision is saved.

Accepted interpretation changes create a current projection while base values and attributed history remain preserved. Related decisions or uses are flagged for review rather than rewritten automatically. A text correction creates a new version and proposed mechanical analysis, inherits its logical section membership, and links to its predecessor/successor. Old readings and alignments remain retrievable. Reattachment candidates are unique exact-string, ambiguous or missing candidates; they are not silently accepted as semantic correspondences. To revise a successor text, target its new permanent ID explicitly. Alternative witnesses/parallel translations can also be added as independent versions in a new dataset.

Authoring appends canonical, ordered JSON events under `edition/proposals/` and `edition/changes/`. **One authoritative project copy writes this journal.** Contributors send downloaded drafts; do not merge journal files from independently edited clones or renumber events. A project lock serializes commands in that copy, not other clones.

New journal format 2 saves the complete observed target context. Historical replay can retain decisions after unrelated base-metadata changes while recording context-review impacts; a changed original target value remains a conflict. Do ordinary metadata corrections through the journal rather than editing base files. Full-row stale checks still apply when a pending proposal is accepted. Format 1 keeps its original stricter replay rules. See the [journal contract](journal-contract.md).

If `.humboldt.lock` remains after an interruption, inspect its recorded PID/time and the running command before removing it. Delete only a confirmed abandoned lock; the engine never removes one automatically. Atomic publication requires a filesystem supporting hard links; FAT/exFAT authoring is unsupported and fails explicitly. Read a copied release there or keep the working copy on a supporting local filesystem. Attribution is recorded, not authenticated expertise.

## Add another passage as data

Use the schema in `src/humboldt/record_schemas/bundle.schema.json` and the explicitly synthetic template `tests/fixtures/minimal/edition/passages/minimal.json` (packaged as `examples/minimal-passage.json` in the release). Supply `format: humboldt.passage`, `schema_version: 1`, a new dataset ID, logical `section`, text-version records, layouts and any evidence/decisions/alignments. IDs are permanent literals; generating another passage must not renumber existing senses. Text hashes cover exact UTF-8 content. Token positions count Unicode code points in that immutable text version.

```bash
./humboldt import /path/to/new-passage.json
./humboldt build --force
```

The importer validates the complete candidate edition before publishing its manifest entry. Paragraph/sentence/rendering and written-token units are generated from layouts. Consequential annotations and many-to-many correspondences are declared as records. No new passage-specific Python builder is needed. This command adds prepared records; it does not translate, infer a parse or invent evidence.

For reviewed apparatus on a journal-created text, add `"requires_versions": ["ACTUAL_NEW_VERSION_ID"]` to the bundle and use that ID in its layouts and alignment records. The importer materializes this data after the required version is created during replay, before subsequent journal amendments. Give layouts new analysis/paragraph/sentence IDs and exact complete body text. Missing dependencies or invalid links reject the import without changing the active manifest. Section membership is inherited even when the title has no `§` number.

New evidence can be imported in a dataset containing `tables.evidence`; its new ID can then support a proposal. The form accepts existing IDs, not invented evidence objects. Supporting attachments under `sources/` and `translations/` are downloadable only when declared/linked and confined to those directories.

## Export and release

```bash
./humboldt export --output build/edition.json
./humboldt export --format csv --table term_sense --output build/senses.csv
./humboldt release --output releases/0.2.0
```

The release contains the runnable engine, durable inputs, current sealed database, guide and file-hash manifest. Packaging validates the copy in a fresh Python subprocess. It does not publish anything. A recipient can run `python3 humboldt validate`, rebuild into `build/`, or browse the included snapshot without the original `tmp/`, legacy scripts, source PDFs or model sessions. Edit a working copy; retain the original release for citation and comparison.

`build/` is disposable output; removing it never removes authoritative inputs. Release destinations and export files must be fresh. `build --force` is confined to project `build/`; it cannot replace source records or historical snapshots. Sealed/read-only SQLite connections prevent accidental edits through normal readers. A database owner can remove SQLite protections, so the durable records, journal and release hashes are the reproducibility evidence.

## Tests and compatibility

```bash
./humboldt test
./humboldt test --legacy
```

The default suite uses synthetic fixtures, generated event-sequence checks, clean portable copies and the real durable scholarly corpus. Legacy tests additionally need original holdings and old snapshots. The real-data regression uses the frozen initial manifest; later approved journal changes or added passages do not invalidate that base comparison.

```bash
./humboldt verify --against edition/baselines/initial.json
./humboldt verify --against releases/0.2.0/release.json
```

The first command checks the explicitly frozen base; the second compares the entire current edition to the selected release and reports intentional differences too. Neither changes data or forces future accepted work to retain an old digest. Local releases and the append-only journal preserve working history; the repository remains uncommitted pending a separate Git instruction.

Inside a portable release, compare its own included edition with `python3 humboldt verify --against release.json`. The `test` commands require the source checkout; `validate` and `verify` also work in the portable package.

SQL migrations remain packaged, checksummed and tested; their command is for advanced inspection/upgrades of unsealed versioned databases. Normal users rebuild sealed outputs. A consistency test checks every scholarly JSON table’s columns against SQL. Record formats stay at version 1 with optional dependency fields; new journal events use version 2 while old version 1 events remain readable. Unknown future formats fail explicitly.

The software preserves source-grounding distinctions. Successful builds, schema checks and interface tests establish computational properties, not German fidelity or the truth of historical linguistic claims.
