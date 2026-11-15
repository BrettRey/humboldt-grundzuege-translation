# Infrastructure verification

Verified locally on 15 November 2026 under D012, using Python 3.14.10. The engine requires Python 3.11+; a multi-version compatibility run was not performed. [Machine-readable evidence](verification.json) records table hashes, protected-file fingerprints, commands and release identity.

**Subsequent review:** [Claude Fable’s architecture review and coordinator checks](reviews/claude-fable-20261115T204942Z/checked-findings.md) identify correction-workflow gaps absent from this test suite. The preservation, integrity and clean-copy results below remain valid for the verified snapshot; they do not establish that corrected versions can receive new apparatus or that later base edits preserve journal replay.

**Resolution:** [D013 correction verification](correction-verification.md) supersedes those workflow limitations for engine 0.2.0. This document and its machine-readable evidence remain the initial infrastructure snapshot; the follow-up records the fixes, 122 checks and current release.

## Preservation

All **33 historical scholarly tables match the original pilot database row-for-row**, including existing identifiers and exact text bodies. The new build retains 21 text versions, 27 analyses, 86,978 units, 1,768 evidence records, 1,575 decisions and 183 alignment groups. All **118 protected files** in the migration baseline retain their SHA-256 fingerprints, including AGENTS.md, original sources, prior translations, sealed terminology inputs, old tools/tests and historical snapshots. No translation was amended.

The logical database identity is:

```text
53334ec49b583ad5538bb21d17249eb8416c38adb14b44874d6ac5027a83a962
```

## Computational checks

- **103 tests pass:** 54 unit, six workflow/integration and 43 historical corpus tests. Current unit/integration runs emit no resource warnings; the preserved historical tests emit their earlier unclosed-connection warnings. Tests cover schema upgrades and tampering, immutability, span/parent/foreign-key failures, stable IDs, data-only import, attributed acceptance/rejection, stale targets, new text versions, old readings, impact records, reader downloads and portable packaging.
- Both the original and clean-copy builds report SQLite integrity `ok`, no foreign-key errors and the same logical digest. The generated database is sealed; readers also use read-only connections.
- A full-data copy containing only `src/`, `edition/`, `humboldt` and `pyproject.toml` validates, rebuilds, searches and traces correctly. It has no `tmp/`, old tools, source holdings, translations or tests. Its subprocesses use a minimal environment without model credentials and with socket connections disabled.
- English search for `understanding` ranks **Verstand** first. The §147 *Andeutung* word trace reaches both the overlapping terminology rule and the sentence-level criterion. Explicit metadata discovers an added synthetic §999 without a new Python builder. Legacy copied §1 labels on §2 English units are preserved as records but no longer override the section titles in discovery.
- Six live reader routes return HTTP 200. A fresh headless browser profile rendered the desktop view; the revised English is selected explicitly, all choices display their permanent IDs, sentence pairs precede additional span alignments, and source text remains in reading order. HTML escaping, loopback binding, attachment confinement and write-free proposal downloads are tested.
- JSON and CSV exports were checked against database identity and table counts. The local `releases/0.1.0/` package includes the engine, schemas, durable records, sealed database, guide, synthetic passage template and file-hash manifest. Packaging validates that copy in a fresh Python subprocess; every listed release-file hash is checked after packaging.

## Reproduction and limits

From the checkout, run `./humboldt test --legacy`, `./humboldt validate --sources`, and `./humboldt build --output build/fresh-check.sqlite`. Legacy tests and optional attachment checks need the original holdings; the current engine and reader do not. See the [user guide](user-guide.md) for normal authoring and release commands. [Migration provenance](../../edition/provenance/legacy-migration.json) is historical evidence, not a build dependency.

The revision apparatus currently supports text bodies, terminology definitions/rules/cautions and decision resolutions. Other scholarly record changes require a prepared dataset/schema change rather than an unrestricted form. Attribution is recorded, not authenticated. Reattachment candidates require semantic review. Source-critical uncertainty, model-assisted quotation checks and the absence of specialist German validation remain unchanged. The package is a local research release; the repository is uncommitted and nothing was published.
