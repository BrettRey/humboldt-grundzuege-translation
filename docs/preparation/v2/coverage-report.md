# Terminology completion: coverage and accuracy

**Snapshot notice (15 November 2026):** the counts and checks below describe the completed terminology stage under D008–D009. The later [§147 pilot assessment](../../../translations/difficult-147/comparison.md) records the additional translation test; its cumulative store preserves this terminology layer.

The individual termbase completes the preparation defined under [D008](../../../DECISIONS.md), replacing the earlier unsupported claim that 34 grouped discussions demonstrated complete terminology coverage. Start with the [alphabetical term index](../termbase.md). The original register, translation versions and source files are preserved.

## What is complete

| Component | Result |
|---|---|
| Main-text terminology review | All 110 printed pages, 364–473 (PDF374–483) |
| Source-image work | Three readers report checking all 110 main-text pages and their selected quotations; coordinator checks at additional recorded contexts |
| Individual records | 1,048 headwords: 1,045 from Grundzüge and three supplementary translation-policy terms |
| Local interpretation | 1,518 working sense/use groups, retaining 1,531 local uses |
| Primary support | 1,566 evidence records; 1,368 distinct source/page/quotation combinations |
| Discovery inventory | All 3,515 range-specific surface candidates dispositioned; 2,477 distinct spellings across the three ranges |
| Earlier register | All 119 labels mapped explicitly to a headword, variant, phrase or derivational/qualified-use note |
| Comparative controls | 87 records with 149 explicit term/control links; 122 term relations |
| Independent audit | One completed bounded pass; all 12 findings dispositioned |
| Software verification | 39 tests pass; SQLite integrity `ok`; no foreign-key errors |
| Preserved inputs | All 33 baseline files retain their SHA-256 values |

Headwords include consequential contextual vocabulary, phrases and editorial lookup lemmas, not only established technical terms. Inflections are not separate headwords. The sense/use count is **not** a count of demonstrably distinct dictionary senses: working groups preserve local bearers, contrasts and rendering conditions. Several terms can cite the same sentence. Each operational use has its own primary support; quotation count is not a measure of independent confirmation.

## How selection and omission were checked

The readers revisited three complete ranges: 364–399, 400–444 and 445–473. They looked for definitions, explicit contrasts, philosophical/psychological vocabulary, linguistic operations, grammatical labels, sound/prosody, classificatory language and consequential metaphors. Each page has an omission-check record. This reading supplies phrases and lowercase expressions that the mechanical inventory can miss.

The reproducible inventory selects capitalized German-form tokens of at least three letters and specified technical lowercase families. It deliberately admits ordinary words, headings, apparatus, cited examples and OCR noise. A form recurring in two ranges receives two review records, not two headwords. Its final dispositions are:

| Disposition | Records |
|---|---:|
| Included, linked to a term | 1,860 |
| Ordinary contextual word excluded from the termbase | 1,321 |
| OCR noise | 123 |
| Proper name or language label | 102 |
| Cited linguistic example | 65 |
| Apparatus only | 44 |
| Unresolved candidate | 0 |

The [structured catalog](../../../sources/terminology/v2/termbase.json) contains every reason, target, page review and reader limit. [Reconciliation](../../../sources/terminology/v2/reconciliation.json) records coordinator corrections rather than silently rewriting reader returns. Excluded words remain in the searchable OCR. Candidate dispositions are form/page-level terminology-selection decisions; they do not classify every occurrence semantically. The 39,132 OCR written-token candidates and 4,740 overlapping family matches remain a discovery layer, not certified frequencies.

## What the evidence means

Checked quotations and uncorrected OCR windows are separate texts. Each main-text quotation has an exact, unique OCR locator window plus printed/PDF/scan coordinates from the actual page map. Corrections to the quotation do not alter the OCR or pretend that its spelling was checked. Supporting-source quotations identify their own work and PDF, without claiming a Grundzüge OCR anchor.

There are 1,561 direct-occurrence records, two supporting-context records, two page-divided word fragments and one elliptical phrase. The fragments reconstruct **Schöpfungsvermögen** across 424–425; they do not make *vermögen* an independent variant of that compound. The elliptical **bezeichnender Begriff** has separately anchored parts, not a falsely contiguous quotation. Supporting words such as *Operationen* do not become variants of *Form*. Lookup spellings are labelled checked, OCR-only, editorial or explicitly rejoined.

The earlier 13 Adelung articles were retained. Twenty-two additional articles were read in the BSB digital 1811 edition; three unrelated homograph articles are explicitly inapplicable, leaving 19 additional applicable controls. These are digital-entry readings, not scan collations. Native search uses ISO-8859-1; an initial UTF-8 false-negative was corrected and recorded. Dictionary range constrains English choices without establishing Humboldt’s local doctrine. Earlier dated primary and focused scholarly controls remain available; additional Manchester chapter7 reading was limited to printed137–138 and141. No whole-book reading is claimed. See the [lexicon record](../../../sources/terminology/v2/lexicon/retrieval.json), [comparative controls](../../../sources/terminology/v2/comparative-controls.json) and [earlier reading ledger](../reading-ledger.md).

## Corrections and independent scrutiny

The [audit dispositions](audit-dispositions.md) explain every finding and its source-based resolution. The completed independent packet contained 26 draft terms, 22 exclusion examples and seven full source pages. It did not inspect images or all final headwords. An earlier full-source Claude request timed out without a usable response and contributes no evidence. Final corrections were checked by readers/coordinator; a second independent audit of the final catalog is not claimed.

Important changes include bearer-conditioned *Vermögen*, faculty versus idiomatic *Verstand*, the full fixed-word-order condition for strict grammatical form, individual standpoint preceding language in *Weltansicht*, the Satz/Periode distinction, and wider evidence for Form, Symbol and Zeichen. The proposed universal Form definition and the audit’s apparatus-only inference about Symbol were rejected where the fuller source did not support them. An initial middle-reader method interleaved margins/apparatus; the reader stopped that method and replaced affected excerpts after image checks. That failure and correction remain recorded.

## Remaining source limits

- The 1906 print remains the provisional base under D001. The modern critical edition and manuscript have not been checked; the reported cancellation of §§1–7 remains unresolved.
- Printed448’s **unter demselben Satz** is retained as an unresolved print reading. It is not silently emended to an accent term or used to manufacture a new Satz sense. Printed462’s marginal **42.** is located as §142 from sequence, with the printed numeral discrepancy retained.
- Selected historical-language examples, Greek/foreign characters and damaged apparatus are not certified by these terminology quotations. Check any example used in a translation against its image. The complete OCR has not been proofread.
- Image checks and interpretive review are model-assisted. No specialist human validation or universal word-by-word sense annotation is claimed. Historical hierarchies and linguistic theories remain attributed to Humboldt.

These limits do not leave an unexamined candidate remainder within the defined preparation. Reopen a particular rule when a checked passage conflicts with it. Existing §§1–2 remain unchanged; this stage adds no §3 translation. [D009](../../../DECISIONS.md) records the provisional use of this termbase. [The store guide](store-guide.md) explains how to reproduce and query it.
