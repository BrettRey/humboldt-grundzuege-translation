# Reading coverage and verification
<!-- SUMMARY: Earlier full-text and supporting reading, plus later all-page v2 terminology checks; no certified transcription or whole-corpus reading · status: updated coverage ledger · updated: 2026-11-15 -->

**Status update — 15 November 2026:** the reading history below is cumulative. The earlier 24-page image sample is preserved as the record of that stage; the later v2 pass adds reported image checks and terminology reviews for every main-text page. See the [v2 coverage report](v2/coverage-report.md) for the completed candidate/page accounting and [current store guide](v2/store-guide.md) for the implementation.

The complete 110-page main text was divided among three Codex model readers. Each reports reading every supplied page, including examples and apparatus. The coordinator checked selected consequential contexts and synthesized the argument map and register. This is model-assisted full-text reading, **not** a human specialist's complete reading or a full visual collation.

| Reader | Complete supplied span | Original report and evidence |
|---|---|---|
| read_early | Printed 364–399, 36 pages | [Report](readings/reading-early.md); [22 records](../../sources/terminology/readings/early-evidence.json) |
| read_middle | Printed 400–444, 45 pages | [Report](readings/reading-middle.md); [22 records](../../sources/terminology/readings/middle-evidence.json) |
| read_late | Printed 445–473, 29 pages | [Report](readings/reading-late.md); [22 records](../../sources/terminology/readings/late-evidence.json) |

[coverage.json](../../sources/terminology/coverage.json) records every page's actual printed/PDF/scan coordinates, reader, image-context status and input fingerprints. The original reports give page-by-page maps and corrupt examples. No supplied main-text page is omitted from the reported reading.

In the earlier preparation, readers and coordinator inspected selected contexts on 24 distinct main-text pages: 373, 379, 387, 395, 399, 401, 403, 410, 419, 420, 426, 427, 428, 441, 443, 449, 455, 456, 459, 462, 469, 470, 471, 473. These checks establish the cited contexts, not every word on those pages. Printed 462's marginal number reads 42.; §142 is identified by sequence.

## Supporting reading completed

The [early primary report](readings/primary-early-reading.md) covers 58 supplied pages: comparative essay 12, forms selections 18 and complete Agamemnon introduction 28. The [later primary report](readings/primary-later-reading.md) covers 35: Lettre conclusion 4, Chinese paper 16 and Kawi selection 15. The [secondary report](readings/secondary-reading.md) covers the assigned Manchester and Underhill sections and complete Trabant chapter/footnotes. Its exact spans and image checks are listed there. These are full readings of the **assigned excerpts**, not their surrounding volumes.

The coordinator additionally read targeted Nord 2006 passages and 13 Adelung digital entries. The dictionary retrieval record includes original HTML fingerprints, exact URLs and preserved text copies. Entry reading does not imply scan collation. The earlier opening research already supplied checked American-fragment and Essai contexts; this stage does not claim a new complete reading of those works.

## Audit and synthesis

Two of the source readers made one further register audit within their existing coverage. They were informed source readers, not blinded fresh translators or independent manuscript witnesses. Six findings have accepted dispositions. Additional local image checks supplied missing occurrence evidence and sharpened two rules; [the audit record](../../sources/terminology/register-audit.json) preserves the findings and responses. T34 was added afterward by the coordinator from the checked source packet.

The shared [evidence records](../../sources/terminology/evidence.json) retain each reader's provenance, source hash, locator, quotation/paraphrase status and caveat. The raw reports remain unchanged after synthesis. A reader's image-checked claim is attributed to that reader unless the coordinator separately checked it. Model agreement has no special verification status.

## Later v2 terminology review

The three readers revisited their complete main-text ranges and report checking all 110 page images and the short supporting quotations for the operational uses. Every page has an omission-check record, and every one of the 3,515 range-specific discovery candidates has a disposition. All 119 labels from the earlier grouped register were reconciled. The resulting 1,048 headwords and 1,518 working sense/use groups retain 1,531 local uses and 1,566 primary evidence records; those groups are not asserted to be distinct dictionary senses or an exhaustive semantic coding of every token.

The additional historical-lexicon pass read twenty-two Adelung articles, with three unrelated homographs excluded and nineteen further applicable controls. Manchester chapter 7 was additionally checked only at printed 137–138 and 141. Together with the thirteen earlier dictionary articles, these are bounded controls, not complete dictionary or book reading. Their provenance is in the [v2 lexicon record](../../sources/terminology/v2/lexicon/retrieval.json) and [comparative controls](../../sources/terminology/v2/comparative-controls.json).

One completed bounded independent v2 audit examined 26 draft terms, 22 exclusion examples and seven source-control pages; all twelve findings have dispositions. It did not inspect all final records or images. An earlier whole-source Claude attempt timed out without usable output and supplies no audit evidence. The [audit report](v2/audit-dispositions.md) distinguishes accepted corrections, qualified claims and rejected inferences. No independent audit of the final whole termbase is claimed.

## Remaining limits

The main extraction still contains OCR errors, running heads and editorial notes. A labelled Tesseract recovery improves the search stream on 410; it does not certify that page. Individual non-German examples and section markers remain unsafe for exact reuse. Translation-stage image checks remain necessary.

The forms essay's 295–305 gap, the surrounding Manchester endnotes, remaining book chapters and most acquired references were not read in this stage. The full corpus inventory is an acquisition record, not a reading-completion claim. The modern critical edition and manuscript evidence have not been checked under D001; the recorded acquisition passes did not obtain their full text. Printed448’s *unter demselben Satz* remains unresolved, and the printed marginal numeral on 462 is preserved despite its sequence-based identification as §142. These limits do not prevent the completed provisional terminology preparation; they do prevent claiming exhaustive scholarship or a critical text. The complete OCR has not been corrected or proofread, and page-image terminology checks do not certify every example, apparatus span or character.
