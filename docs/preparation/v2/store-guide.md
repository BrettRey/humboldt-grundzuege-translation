# Individual termbase: store and reproduction

**Snapshot notice (15 November 2026):** this guide records the completed terminology-stage snapshot. The later [§147 pilot guide](../../../translations/difficult-147/store-guide.md) identifies the current cumulative database and verification; the commands and counts below reproduce the preserved terminology stage.

Use [the term index](../termbase.md) for reading. The machine input is [termbase.json](../../../sources/terminology/v2/termbase.json); JSON preserves exchangeable records, while SQLite provides the linked database Brett requested.

The terminology-stage cumulative snapshot is `tmp/termbase-v2/termbase-final.sqlite`, with a readable export at `tmp/termbase-v2/termbase-final.csv`. Both are reproducible local artifacts, ignored by Git. Earlier snapshots and translation versions remain preserved.

## Rebuild and verify

Run from the repository root with Python3 and the recorded local sources. No package installation, server or network is needed. Use fresh paths for candidate, database and CSV outputs.

```bash
python3 tools/terminology_candidates.py --output tmp/candidates-fresh
python3 tools/assemble_termbase.py --output sources/terminology/v2/termbase.json
python3 tools/render_termbase.py
python3 tools/termbase_store.py build --db tmp/termbase-fresh.sqlite --csv tmp/termbase-fresh.csv
python3 -m unittest discover -s tests -v
```

Candidate generation reproduces the saved inventories; it does not perform interpretive review. Assembly applies explicit reconciliation to the preserved reader returns, validates all candidate/page/legacy-label coverage and exact quotation anchors, and fails on unresolved structural issues. Build verifies input and comparative-source hashes, imports the previous cumulative store unchanged, then adds the individual records. Rendering regenerates the index and four alphabetical Markdown files. It does not overwrite the coverage report, audit dispositions or earlier 34-group register.

## Find a word, sense and source

```bash
python3 tools/termbase_store.py query --db tmp/termbase-v2/termbase-final.sqlite --term Verstand
python3 tools/termbase_store.py query --db tmp/termbase-v2/termbase-final.sqlite --term Organe
python3 tools/termbase_store.py query --db tmp/termbase-v2/termbase-final.sqlite --term 'grammatische Form'
python3 tools/termbase_store.py trace --db tmp/termbase-v2/termbase-final.sqlite --unit 'tbquote:lex:verstand:s01:e01:expression'
```

Lookup accepts an exact saved headword/form after case, whitespace and Unicode normalization; it does not silently stem words or equate unrelated compounds. Results give form status, sense/use rules, evidence, source coordinates, relations and controls. `Organe` reaches `Organ`. `Denkenden` reaches `Denkender`, not `Sprechender`. There is no promise that every unsaved inflection has an alias.

Tracing a checked expression returns its attestation and sense. Tracing a word in an OCR locator window returns a labelled **context association**, not an automatic sense assignment to that word. Only the selected checked expression, or an explicitly typed part of it, carries the term link. Existing paragraph/clause/word alignments for §§1–2 are retained; the rest of the book has not received equivalent translation alignments.

Example direct SQL for checking a local use:

```sql
SELECT l.headword, s.label, a.printed_page, a.pdf_page,
       a.evidence_role, e.excerpt
FROM lexeme l
JOIN term_sense s ON s.lexeme_id = l.id
JOIN sense_attestation a ON a.sense_id = s.id
JOIN evidence e ON e.id = a.evidence_id
WHERE l.headword = 'Verstand'
ORDER BY a.printed_page;
```

## What the tables preserve

| Tables | Purpose |
|---|---|
| `lexeme`, `lexeme_form` | Individual headword, role/scope and typed lookup spellings |
| `term_sense`, `term_use`, `sense_rendering` | Working interpretation groups, retained local uses and ordered English candidates |
| `sense_attestation`, `term_expression_part` | Checked quotation/expression, separate OCR locator, source layer and exact coordinates |
| `composite_attestation`, `composite_member` | One compound split across two printed pages, retaining both fragments |
| `term_relation` | Explicit, qualified links between terms |
| `terminology_candidate`, `terminology_page_review` | Selection dispositions and all-page omission checks |
| `register_carry_forward` | Disposition of all 119 earlier labels |
| `terminology_control`, `lexeme_control` | Source-grounded comparisons, attached explicitly to relevant terms |
| Earlier text/unit/alignment tables | Immutable versions, proposed analyses and existing translation links |

The snapshot contains 15 text versions, 21 analyses, 82,969 units, 1,747 evidence records, 1,565 decisions and 84 alignment groups. Its new layer has 1,048 headwords, 1,518 sense/use groups, 1,531 local uses and 1,566 primary attestations. These table counts include the earlier work; neither token counts nor decision counts certify linguistic adequacy.

## Limits of verification

The 39 passing tests check reproduced inventories, complete dispositions, coordinates, exact anchors, text/span recovery, the separation of OCR and checked text, typed fragments, lookup behavior, historical-control links, preserved inputs and database integrity. They are not a German-meaning benchmark. The full test run also emitted pre-existing unclosed-connection ResourceWarnings; it completed successfully.

The [coverage report](coverage-report.md) defines the completed scope and unresolved source readings. [Audit dispositions](audit-dispositions.md) separate accepted corrections from rejected inferences. [verification.json](../../../sources/terminology/v2/verification.json) records final counts and hashes. Any future English change needs a new text version and linked decision; updating a glossary does not silently revise a sealed translation.
