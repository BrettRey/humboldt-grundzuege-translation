# Linked-text database prototype
<!-- SUMMARY: Preserved opening-only SQLite prototype; later bounded adoption and cumulative v2 implementation supersede pending-status claims · status: historical prototype · updated: 2026-11-15 -->

**Supersession notice — 15 November 2026:** the body below records the 14 November source-only prototype and its then-current limits. [D002 and D004](../DECISIONS.md) subsequently authorized the opening comparison cycles, which are complete for §§1–2. The store now preserves their English versions and many-to-many alignments; the later [v2 cumulative implementation](preparation/v2/store-guide.md) also adds whole-work discovery and individual terminology evidence. The earlier counts, no-English-import statement and pending-adoption language below apply to this prototype only. Neither implementation nor English review certifies German fidelity.

## Purpose and scope

Test Brett’s requested links between individual words, clauses, sentences and paragraphs using the checked German opening. SQLite is already installed; Python’s standard library is sufficient. The generated database stays under ignored `tmp/` until the design is reviewed. Its contents are research annotations, not a validation of the translation.

The existing pilot and workflow-review document remain frozen. This prototype prepares the source and evidence layer independently of a translation comparison. No English candidate is imported, so the store cannot leak the old draft into a later blind comparison.

## Implemented records

- **Text versions:** title, source file and hash, exact immutable UTF-8 text, language, transcription provenance and scope. New readings create new versions. A separate bibliographic document table is deferred.
- **Analyses and units:** a named analysis records its method, scope and review status. Units identify spans as paragraphs, excerpts, sentences, proposed clauses, predicate/phrase annotations or written words. Alternative analyses coexist without changing the text. Punctuation is not separately stored.
- **Evidence:** source location, short quotation, commentary and verification status. A verified quotation in a secondary source remains distinct from verification of the underlying historical claim.
- **Decisions:** question, provisional or adopted resolution, and links to relevant units and evidence. D001 supplies the initial editorial-policy example.
- **Alignments:** a group can contain several units on each side. This supports many-to-many links without forcing every word or clause into a one-to-one translation. Initial examples compare German wording between the two fragments, with correspondence type and status explicit.

Offsets use zero-based Unicode code points and half-open ranges: `[start, end)`. Extracted text is always calculated from the stored version. Word tokenization is an explicitly recorded convention for written forms, not a grammatical analysis. Clauses remain proposed annotations.

## Minimum safeguards

Require foreign keys, valid spans, agreement between a unit’s version and analysis, and containment of any parent span. Preserve text versions and unit records; revise an analysis by adding another analysis. A completed alignment needs members on both sides. Changing the source cannot silently move old annotations onto new wording.

The importer verifies source hashes and rejects ambiguous quote matches. The prototype must demonstrate a query from a word to its sentence, paragraph, evidence and decision, and a grouped alignment with multiple members on each side.

## Checks and stopping rule

Build one database from the opening and one short parallel excerpt. Check exact text round trips, Unicode offsets, source fingerprints, hierarchical links, evidence retrieval and alignment membership. Attempt invalid inserts and mutations to ensure the relevant constraints reject them. Run SQLite’s integrity and foreign-key checks.

Stop after this demonstration and a bounded design review. Retain disagreements and known limits for Brett’s review. A user interface, global catalogue integration, full-corpus import, linguistic parser, production migration system and later translation units are outside this prototype.

## Reproduce the demonstration

From the repository root, with the two source PDFs listed in the packet present:

```bash
python3 -m unittest discover -s tests -v
python3 tools/alignment_store.py build --db tmp/alignment-demo.sqlite
python3 tools/alignment_store.py demo --db tmp/alignment-demo.sqlite
```

Choose a fresh output path for each build; an existing database is never overwritten. The current instance is [tmp/alignment-prototype.sqlite](../tmp/alignment-prototype.sqlite). Reusable inputs are [the source packet](../sources/annotations/opening-001.json), [Python tool](../tools/alignment_store.py), [SQL schema](../tools/alignment-schema.sql), and [tests](../tests/test_alignment_store.py). The packet is a JSON import artifact; SQLite performs the relational queries.

The current build contains two text versions, four analyses, 376 units, four evidence records, D001 and one alignment group. Fifteen tests pass, including all span round trips, combining marks and an emoji, hash failures, ambiguous quotes, invalid parents, immutable records, wrong-version alignments and missing alignment sides. SQLite reports `integrity_check: ok` and no foreign-key errors. These are software checks, not a German fidelity audit.

## Design review and limits

Muse **muse-wonder-full-1.0** recommended narrowing the design and separating quotation checking from claim validation. Both were adopted. Explicit parents were retained for the ancestry query, and the tiny parallel excerpt permits a real two-to-two example. Claude **claude-fable-5-2** supplied proposed clauses; the coordinator added a separately labelled s7 alternative. No analysis is canonical.

The database has no user interface or access-control system: `reviewed` and `adopted` are recorded research statuses, not mechanically enforced human authority. D001’s adopted status applies only to the source policy. Source/body hashes are checked by the importer, rather than by a built-in SQLite hashing function. Use the supplied connection helper, which enables foreign keys. Text and analysis revisions require new records; general annotation editing and lifecycle management are deferred. Code-point offsets need conversion for browser UTF-16 APIs or grapheme-based display. The word convention is documented, not linguistically certified. No adoption or integration into the translation workflow has occurred.
