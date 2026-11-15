# §147 pilot: linked store and reproduction

The current cumulative snapshot is `tmp/difficult-147/pilot.sqlite`. It preserves the entire previous terminology database and adds the checked German, three isolated candidates, pre-audit synthesis, revision, source notes and consequential judgments for the complete §147.

## Rebuild

From the repository root, using the held sources and preserved earlier snapshot:

```bash
python3 tools/build_difficult_pilot.py --db tmp/difficult-pilot-fresh.sqlite
python3 -m unittest discover -s tests -v
python3 tools/termbase_store.py query --db tmp/difficult-147/pilot.sqlite --term 'grammatische Form'
```

The builder requires a fresh output path, verifies recorded source/input hashes, reconstructs the earlier store from its inputs, and adds the pilot. [record.json](record.json) contains input hashes and actual runtime model identities. [baseline.json](baseline.json) protects 82 earlier source/translation/termbase artifacts, including the old SQLite snapshot. [verification.json](verification.json) records final checks. The prior v2 verification remains a dated snapshot, not a promise that subsequently updated status Markdown retains its old hash.

The snapshot has 21 text versions, 27 analyses, 86,978 units, 1,768 evidence records, 1,575 decisions and 183 alignment groups. The pilot adds 90 source-sentence/rendering links across five English versions and nine selected span links. Six selected German occurrences are connected to existing conditional termbase rules. Paragraphs, words, alternate versions and judgments remain separately identifiable.

For a word’s sentence ancestry, primary evidence and sentence-level decisions, the existing Python API is available:

```python
import sys
sys.path.insert(0, "tools")
import alignment_store

db = alignment_store.connect("tmp/difficult-147/pilot.sqlite")
try:
    result = alignment_store.trace_word(db, "difficult-147-de-v1:s05:w001")
finally:
    db.close()
```

The API’s ancestor trace does not automatically include overlapping sibling clause or term units. Those are available by span containment in `unit_text`, then through `unit_decision`, `alignment_member` and `alignment`. This distinction prevents a context word from silently acquiring every nearby term’s interpretation.

English rendering blocks may contain several English sentences; they are labelled as rendering blocks, not falsely counted as one English sentence. Source sentence IDs are an analysis of the checked print, not authorial identifiers. Selected clause/phrase links are proposed correspondences, not certified equivalence or a complete parse.

## Verification scope

The tests check complete source and version coverage, exact critical spans, the shared scope correction in s05, the independent word-order condition, negation and evidential-limit guards, every audit disposition, frozen candidate inputs, source/target substring recovery, preserved old rows and integrity. Those software checks do not certify meaning. The [pilot assessment](comparison.md) gives the substantive evidence and limits; the [revised English](revised.md) awaits English/editorial review.
