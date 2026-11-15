# Earlier terminology discovery store

**Supersession notice — 15 November 2026:** the commands, counts and T01–T34 examples below document the earlier discovery/group-register snapshot. The current cumulative implementation is [the v2 SQLite termbase](v2/store-guide.md), at `tmp/termbase-v2/termbase-final.sqlite`, with individual term/use/evidence links and preserved earlier alignments. See the [term index](termbase.md) and [coverage report](v2/coverage-report.md). Retain this guide for reproduction of the earlier layer; its 34-entry count is not a current coverage claim.

The earlier cumulative snapshot is [preparation-complete.sqlite](../../tmp/preparation/preparation-complete.sqlite). It contains the existing paragraph, clause, word and alignment records plus the whole-work discovery index, 34 terminology entries, 155 preparation evidence records and their decision links. SQLite is the queryable relational store; JSON holds reproducible exchange/build inputs. The Markdown register is a reader-facing rendering of those inputs.

## Rebuild and query

Use a fresh output path; the tool refuses to overwrite a snapshot. Held source files must match their recorded SHA-256 values. No downloads occur during a build.

```bash
python3 tools/preparation_store.py build --db tmp/preparation-check.sqlite --concordance tmp/concordance-check.csv
python3 tools/preparation_store.py query --db tmp/preparation/preparation-complete.sqlite --term T13
python3 tools/preparation_store.py query --db tmp/preparation/preparation-complete.sqlite --word Weltansicht
python3 tools/preparation_store.py query --db tmp/preparation/preparation-complete.sqlite --family type --limit 100
python3 -m unittest discover -s tests -v
```

The [CSV concordance](../../tmp/preparation/concordance-complete.csv) exports term-family matches with token, printed/PDF/scan coordinates, extraction status and unit ID. It is a discovery aid, not a semantic annotation export.

If an input rule changes intentionally, regenerate its Markdown with `python3 tools/render_terminology.py`, then build a new database snapshot. Do not edit an existing text version's body under its old ID.

## What the links mean

`text_version → analysis → unit` retains immutable text identities and Unicode code-point spans. Existing §§1–2 have paragraph/sentence/word units, proposed clauses and many-to-many English alignments. The new whole-work version has page units and written-token candidates; no automatic clause parse of all 110 pages is claimed.

`word_index` supplies casefolded lookups while preserving the indexed token and offsets. `term_occurrence` links broad regex families to candidate units. `term_entry_family` links those families to conditional register entries; that does **not** assert that every family hit instantiates the entry's sense.

`term_entry → decision` records a provisional rendering rule. `term_entry_evidence` and `decision_evidence` link it to exact source locators, statements and verification status. `evidence_detail` retains fuller reader provenance and issues. Evidence with a single main-text page additionally links to that page unit; range records retain their exact locators. Corrected image readings are not falsely anchored as verbatim spans in uncorrected OCR. Existing checked §§1–2 source-word units additionally link to relevant register decisions, preserving their old decisions and alignments.

For example, T23 leads to the rule on supplied/marked grammar, its later source contexts and C24's word-order condition. T27 links back to §1's Verkehr word and the historical dictionary entry. T13 leads to the world-view rule and occurrences of Weltansicht; a search hit by itself does not establish the same sense.

## Limits of discovery counts

The index joins line-end hyphens within pages and collapses whitespace. It preserves a labelled recovered OCR stream for printed 410 while leaving the original extraction unchanged. Cross-page divided words are not rejoined; capture errors remain. Casefolding helps spelling lookup but is not historical lemmatization.

Only the first nonblank line is labelled `header_candidate`; this heuristic neither removes all headers nor separates active main text from apparatus. `body_or_note` is not a certificate of authorial wording. Family matches overlap and include false positives. The Typus family in particular has many running-head hits. Frequencies therefore describe this discovery stream, not certified lexical occurrences or conceptual importance.

Numerical checks establish source fingerprints, spans, page coverage, referential integrity and preserved earlier versions. They do not establish German fidelity or interpretive truth. Further exact occurrence coding belongs to a bounded later passage task, when its source images are checked.
