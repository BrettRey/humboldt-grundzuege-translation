# Annotation application report
<!-- SUMMARY: Approved policy applied to the existing translations · status: reader review completed; terminology clarification applied · updated: 2026-11-16 -->

**Review response:** Brett completed the reading review and asked whether substantive needed clarification at147:s17. The existing note and terminology entry now define it through the use/employ example. The [review record](review.json) and [response](reviews/2026-11-16/response.md) preserve the exact comment, original files and attributed corrections. The 27-note sequence and all English main text remain unchanged. Completion does not certify German fidelity or imply separate approval of the new wording.

## Result and scope

The [annotated reading](reading.md) applies the [approved footnoting policy](../../docs/footnoting-policy.md) to Introduction 1–7, Part I opening 8–15 and the separate later pilot 147. It contains 27 footnotes in one Arabic sequence, with **(Humboldt)**, **(1906 Ed.)** and **(Trans.)** attribution, plus nine short terminology entries. No passage beyond this existing selection was translated.

All 107 source/rendering blocks and all 16 English version bodies are unchanged. Passage 7 retains its two printed paragraphs. The earlier [Introduction](../introduction/revised.md), [Part I opening](../part-i-opening/revised.md) and [pilot](../difficult-147/revised.md) remain intact, along with their candidates, audits, comparisons and review states.

## What was selected

Local notes expose consequential alternatives: the temporal/exceptive reading in 1, pronoun references in 2, the possessive and sound-designation readings in 5, the genus shift in 7, system and forms/thoughts in 9, joint working in 14, and the form/indication referent in 147. Unfamiliar uses such as idiom, period and substantive receive short explanations. The previously approved note on Humboldt’s American publication programme is retained verbatim before its citations.

Recurring mental, classificatory and grammatical vocabulary belongs in the terminology guide. It expressly identifies the inherited English variation for *Seele* without inventing a source lexical contrast or silently changing the translation. Routine stylistic alternatives and explanations already clear in the English remain in the apparatus. The [49-item disposition ledger](dispositions.json) accounts for the notes in the current section copies and their earlier paragraph reading copies; it does not replace the complete [Introduction](../introduction/comparison.md), [Part I](../part-i-opening/comparison.md) or [pilot](../difficult-147/comparison.md) audit dispositions.

The title note explicitly summarizes the 1906 editor’s apparatus. The pilot preserves Humboldt’s complete source citation, with an English title gloss and its unexplained terminal “98.” The editor’s separate page reference is translated and attributed. Its original nested position is recorded; display callouts are flattened beside the author’s callout to keep one ordinary sequence.

## Evidence and limits

Focused notes distinguish alphabetic writing from Maya writing, qualify the unrestricted English gender claim, explain the historical scope problem in “German,” and clarify the Greek and Coptic comparisons. [The source records](notes.json) give URLs, locators and the support actually inspected. Parks Canada, Lehmann, Smyth and the relevant Plumley sections were read; the Maya and Cambridge additions rely on primary-site search excerpts because full live-page retrieval failed. The record does not claim complete inspection of those pages.

The Danish s-passive’s existence was checked. The limited Greek-dual check establishes its older use, not its subsequent disappearance; that historical claim remains uncertified. The precise intended Coptic construction, scope of “German,” historical extension of *Nomen* and function of “98.” remain unresolved. This is a bounded annotation pass, not a new audit of every historical claim or a fresh translation comparison cycle. The reported cancellation qualification remains limited to Introduction 1–7.

## Records, reproduction and review

[Note records](notes.json) retain permanent IDs, display-number mapping, authorship, English body hashes, offsets and German/English unit links. The [generic dataset](../../edition/passages/reader-footnotes-v1/records.json) links 36 annotation decisions and 43 evidence records to existing units. Explicit version dependencies ensure that the revised English in 1 and 4 exists before its notes load. No engine, journal or text-version change is needed.

From the repository root:

```bash
python3 tools/render_annotated_reading.py
./humboldt validate --sources
./humboldt build --force
./humboldt trace 'intro:p1:clarified:s6'
./humboldt test --legacy
```

The renderer checks that the reading matches its frozen English inputs and current annotation text after journal replay; the immutable base note records remain available. `--write` explicitly regenerates it and refuses to overwrite CriticMarkup; preserve and resolve review feedback first. An optional local preview uses existing Pandoc: `pandoc translations/annotated/reading.md --standalone -o build/annotated/reading.html`.

[Verification](verification.json) records 134 passing checks, unchanged earlier rows in all 33 scholarly tables, all 118 protected file hashes, all 116 previously tracked translation-file hashes, and unchanged journal/impact rows. The HTML check finds exactly one Arabic 1–27 sequence with complete targets. Software tests establish preservation and traceability. Brett’s completed review concerns English clarity and usefulness; it cannot certify German fidelity. The original verification below predates the clarification; review-response checks are recorded separately in the review record. The [pass record](record.json) preserves the exact inputs and limits.
