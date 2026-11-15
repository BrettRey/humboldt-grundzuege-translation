# Source corpus status
<!-- SUMMARY: Acquisition inventory and access gaps retained; bounded primary/secondary reading and v2 terminology preparation complete; critical text unverified · status: corpus incomplete, preparation complete within defined scope · updated: 2026-11-15 -->

Updated 15 November 2026 (Toronto). **The acquisition inventory remains incomplete; the defined terminology preparation is complete.** The earlier collection pass added twelve PDF/Markdown pairs to the three already held. After Brett completed U of T login, Manchester (1985) and Drechsel (2024) were also acquired as complete publisher section sets. There are now seventeen reference acquisition entries containing sixty-four supporting PDF/Markdown pairs, alongside the main GS V source.

The [manifest](../sources/manifest.json) records provenance, absolute inbox paths, project paths, SHA-256 hashes, and item-specific access checks. Raw files are ignored by Git. Acquisition, reading, and passage verification are separate. Selected primary and secondary passages have now been read and used as controls; the surrounding volumes have **not** all been read, and this work does not certify the translation. Archive OCR and automatic text extraction remain uncorrected. The [reading ledger](preparation/reading-ledger.md) records actual spans and verification levels.

## Current preparation and verification

- **Main text:** all 110 printed pages, 364–473, have reported full-text reading and later terminology reviews. The three terminology readers report checking all main-text page images and their selected supporting quotations; this is model-assisted checking, not a word-for-word certified transcription or specialist human validation.
- **Termbase:** the [individual v2 termbase](preparation/termbase.md) replaces the earlier 34-group register as the working terminology reference. Its 1,048 headwords include contextual vocabulary and three supplementary translation-policy terms. The [coverage report](preparation/v2/coverage-report.md) accounts for every page, all 3,515 discovery candidates and all 119 earlier labels.
- **Supporting reading:** dated Humboldt selections, the complete Agamemnon introduction, focused Manchester/Underhill passages, the complete supplied Trabant chapter and targeted Nord passages have been read. Historical dictionary controls are recorded separately; this is not whole-corpus or whole-book reading.
- **Implementation and reviews:** the [cumulative SQLite store](../translations/difficult-147/store-guide.md) is implemented, preserving earlier text versions and alignments alongside individual terms, local evidence and decisions. The §§1–2 comparison/audit cycles and later reassessment are complete; §1 English review is recorded. The original pilot remains preserved and unvalidated. The separate [§147 pilot](../translations/difficult-147/comparison.md) has completed one comparison/audit/revision cycle; English review is pending.
- **Source-critical gap:** D001 still retains the 1906 print provisionally. The modern critical edition and manuscript have not been checked, so the reported cancellation of §§1–7 remains unresolved. Acquisition/file checks, checked quotations, interpretation and English review have distinct authority.

The [textual-basis options note](preparation/textual-basis-options.md) records the bounded alternative-source check. The 2017 edition is not a prerequisite for declared provisional work. No new full text or manuscript facsimile was acquired in that check.

## Humboldt parallels now held

The collected volumes are edited by Albert Leitzmann, Berlin: B. Behr’s Verlag. Their individual publication years were checked against title pages; the Archive’s generic collection date was not used.

| Requested text | Acquired location | Navigation |
| --- | --- | --- |
| *Essai sur les langues du nouveau Continent* (1812) | GS III (1904) | Printed 300–341; PDF 312–353 |
| *Über das vergleichende Sprachstudium…* (1820 lecture; 1822 publication) | GS IV (1905), plus separate original-publication scan | GS printed 1–34; PDF 11–44 |
| *Über das Entstehen der grammatischen Formen…* | GS IV (1905) | Printed 285–313; PDF 295–323. Checked heading/apparatus dates lecture 17 January 1822 and first print 1825; the assigned excerpts do not establish composition in 1821. |
| *Lettre à Monsieur Abel-Rémusat…* | Existing GS V (1906) | Printed 254–308; PDF 264–318 |
| *Über den grammatischen Bau der chinesischen Sprache* | Existing GS V | Printed 309–324; PDF 319–334 |
| *Untersuchungen über die Amerikanischen Sprachen* | Existing GS V | Opening at PDF 355; keep its variant opening distinct from *Grundzüge*. |
| *Über den Dualis* | GS VI/1 (1907) | Printed 4–30; PDF 14–40 |
| *Über die Verschiedenheiten des menschlichen Sprachbaues* | GS VI/1 | Printed 111–303; PDF 121–313 |
| *Von dem grammatischen Baue der Sprachen* | GS VI/2 (1907) | Printed 337–486; PDF 11–160. Called *Vom grammatischen Baue…* in the recovered brief. |
| Kawi introduction, *Über die Verschiedenheit…* | GS VII/1 (1907) | Printed 1–344; PDF 11–354 |
| Introduction to Humboldt’s *Agamemnon* translation (1816) | GS VIII (1909) | Printed 119–146; PDF 129–156 |

These locations come from contents lists, headings, and boundary-page text checks. They support navigation, not a certified visual map or full collation of every page.

## Acquired supporting files and file checks

Each link below points to the final inbox file. Identical project copies are in `sources/raw/references/`; their paths and hashes are in the manifest. The twelve PDFs from the earlier collection pass parse successfully, have nonempty Markdown sidecars, and match their project copies. Its ten Archive PDFs and supplied OCR files also match the Archive’s recorded sizes and MD5 checksums.

| Work / scope | PDF | Markdown |
| --- | --- | --- |
| Humboldt GS III, 394 PDF pages | [PDF](/Users/brettreynolds/pdf-inbox/humboldt-gs-03.pdf) | [MD](/Users/brettreynolds/pdf-inbox/humboldt-gs-03.md) |
| Humboldt GS IV, 456 pages | [PDF](/Users/brettreynolds/pdf-inbox/humboldt-gs-04.pdf) | [MD](/Users/brettreynolds/pdf-inbox/humboldt-gs-04.md) |
| Humboldt GS VI/1, 350 pages | [PDF](/Users/brettreynolds/pdf-inbox/humboldt-gs-06.pdf) | [MD](/Users/brettreynolds/pdf-inbox/humboldt-gs-06.md) |
| Humboldt GS VI/2, 292 pages | [PDF](/Users/brettreynolds/pdf-inbox/humboldt-gs-06-2.pdf) | [MD](/Users/brettreynolds/pdf-inbox/humboldt-gs-06-2.md) |
| Humboldt GS VII/1, 366 pages | [PDF](/Users/brettreynolds/pdf-inbox/humboldt-gs-07-1.pdf) | [MD](/Users/brettreynolds/pdf-inbox/humboldt-gs-07-1.md) |
| Humboldt GS VIII, 286 pages | [PDF](/Users/brettreynolds/pdf-inbox/humboldt-gs-08.pdf) | [MD](/Users/brettreynolds/pdf-inbox/humboldt-gs-08.md) |
| Bernhardi, *Anfangsgründe der Sprachwissenschaft* (Berlin: Frölich, 1805), 449 pages | [PDF](/Users/brettreynolds/pdf-inbox/bernhardi-1805-anfangsgruende.pdf) | [MD](/Users/brettreynolds/pdf-inbox/bernhardi-1805-anfangsgruende.md) |
| Abel-Rémusat, *Élémens de la grammaire chinoise* (Paris: Imprimerie royale, 1822), 268 pages | [PDF](/Users/brettreynolds/pdf-inbox/abel-remusat-1822-grammaire-chinoise.pdf) | [MD](/Users/brettreynolds/pdf-inbox/abel-remusat-1822-grammaire-chinoise.md) |
| F. Schlegel, *Über die Sprache und Weisheit der Indier* (Heidelberg: Mohr und Zimmer, 1808), 351 pages | [PDF](/Users/brettreynolds/pdf-inbox/schlegel-1808-sprache-weisheit-indier.pdf) | [MD](/Users/brettreynolds/pdf-inbox/schlegel-1808-sprache-weisheit-indier.md) |
| Bopp, *Über das Conjugationssystem der Sanskritsprache…* (Frankfurt, 1816), 369 pages including preface and translations | [PDF](/Users/brettreynolds/pdf-inbox/bopp-1816-conjugationssystem.pdf) | [MD](/Users/brettreynolds/pdf-inbox/bopp-1816-conjugationssystem.md) |
| Underhill, *Humboldt, Worldview and Language* (2009), 177 pages; existing local book | [PDF](/Users/brettreynolds/pdf-inbox/underhill-2009-humboldt-worldview-language.pdf) | [MD](/Users/brettreynolds/pdf-inbox/underhill-2009-humboldt-worldview-language.md) |
| Trabant, “The Celebration of Linguistic Diversity…” (2023), complete chapter, printed 308–325; existing local holding | [PDF](/Users/brettreynolds/pdf-inbox/trabant-2023-anthropological-linguistics.pdf) | [MD](/Users/brettreynolds/pdf-inbox/trabant-2023-anthropological-linguistics.md) |
| Previously acquired: Schleiermacher, *On the Different Methods of Translating*, Bartscht translation, 16 pages | [PDF](/Users/brettreynolds/pdf-inbox/schleiermacher-methods-bartscht.pdf) | [MD](/Users/brettreynolds/pdf-inbox/schleiermacher-methods-bartscht.md) |
| Previously acquired: Humboldt comparative essay, original publication, printed 239–260 | [PDF](/Users/brettreynolds/pdf-inbox/humboldt-vergleichendes-sprachstudium-1822.pdf) | [MD](/Users/brettreynolds/pdf-inbox/humboldt-vergleichendes-sprachstudium-1822.md) |
| Previously acquired: Nord (2006), “Translating as a Purposeful Activity: A Prospective Approach,” 13 pages | [PDF](</Users/brettreynolds/pdf-inbox/nfchoiron,+108-128-2-PB.pdf>) | [MD](</Users/brettreynolds/pdf-inbox/nfchoiron,+108-128-2-PB.md>) |

The comparative essay’s Markdown comes from a separately published Wikisource transcription, not the associated image-only PDF. Nord’s article is not her longer book. The two existing local modern works supplement the requested scholarship; they do not replace missing works.

## Modern books acquired after login

- **Manchester (1985), *The Philosophical Foundations of Humboldt’s Linguistic Doctrines*.** U of T licensed access through De Gruyter supplied eighteen unchanged section PDFs. The set includes all front matter, introduction, eight chapters, conclusion, notes, references and indexes: printed i–xii and 1–216. Each file includes an extra publisher cover page.
- **Drechsel (2024), *Wilhelm von Humboldt and Early American Linguistics*.** Cambridge confirmed digital access. Both contents pages were downloaded, including Appendix 2, references and index. Thirty-three listing entries yielded thirty-one byte-distinct PDFs. The canonical thirty-file sequence covers printed i–xviii and 1–346; one additional file repeats Appendix 1 with different footer information and is excluded from that sequence.

The [section index](reference-sections.md) links every final inbox PDF and Markdown file. All forty-nine new pairs and their project copies are verified. Title pages were visually checked; section coverage was checked against contents, boundary text and PDF page counts, rather than a complete visual collation. Eight brief Drechsel paratext files rejected by the normal converter use labelled Poppler extractions; their unchanged PDFs and sidecars completed the normal inbox handoff. Neither book has been fully read.

## Outstanding full texts and observed limits

These are the five full texts not obtained in the recorded acquisition passes. The access observations below are dated history, not a fresh test of present availability. Investigation of alternatives to the 2017 edition is separate and is not reported as complete here.

| Work | Observed state / next route |
| --- | --- |
| Lindorfer/Trabant critical edition (2017), *Von den Sprachen Amerikas zum allgemeinen Typus der Sprache* | [Brill](https://brill.com/edcollbook/title/52943) remained restricted after the earlier U of T login; only a two-page chapter preview was exposed. U of T located a print series record. Humber exact-title and ebook-ISBN searches returned no record during its announced maintenance outage. Full edition not obtained. |
| Lindorfer (2018), “Geht Humboldts Sprachphilosophie auch im Fragment…?” | Exact chapter: printed 151–162, DOI [10.30965/9783846763445_011](https://doi.org/10.30965/9783846763445_011). U of T print ISBN and chapter DOI found no record; title query found book reviews. The [book contents](https://toc.library.ethz.ch/objects/pdf03/z01_978-3-7705-6344-9_01.pdf) verifies the chapter location. The author-hosted lead failed to load; no full text obtained. |
| Di Cesare (1996), “‘Innere Sprachform’…” | *Historiographia Linguistica* 23(3):321–346, DOI [10.1075/hl.23.3.05dic](https://benjamins.com/catalog/hl.23.3.05dic). Two distinct U of T article records resolved to Downsview print holdings and Scan and Deliver. Publisher PDF requires authorization. No scan request submitted. |
| Berman (1999), *La traduction et la lettre…* | U of T ISBN 9782020380560 locates Robarts print copy, P306.2 .B47 1999. Record offers pickup and chapter Scan and Deliver; no online provider displayed. No request submitted. |
| Heath translation, *On Language*, Losonsky ed. (1999) | U of T paperback ISBN 9780521667722 locates print holdings, P103 .H8513 1999. Publisher metadata verifies this edition, but no complete English text was obtained. Other ebook routes remain unexhausted. |

These observations do not prove that every legitimate access route is unavailable. Humber’s displayed outage was scheduled from 6 p.m. 14 November to 8 a.m. 15 November, Toronto time; the additional modern titles were not searched there during that outage. No purchase, external message, scan request, or interlibrary-loan request was made.

## Online reference resources

- [BBAW correspondence](https://wvh-briefe.bbaw.de/): available online; relevant letters involving Abel-Rémusat, Bopp, Duponceau, and Pickering still need selection and passage checking.
- [Adelung](https://woerterbuchnetz.de/?sigle=Adelung): the portal was identified during acquisition; later preparation read thirteen articles and twenty-two additional articles in the BSB digital 1811 edition. Three additional homograph articles were inapplicable, leaving nineteen further applicable controls. These are digital-entry readings, not scan collations; see the [original controls](preparation/primary-and-secondary-controls.md#historical-dictionary-check) and [v2 retrieval record](../sources/terminology/v2/lexicon/retrieval.json).
- [Grimm](https://woerterbuchnetz.de/?sigle=DWB): portal identified; no completed entry reading is recorded in this preparation. Consider its later date before using it as historical evidence.
- [Deutsches Textarchiv](https://www.deutschestextarchiv.de/): dated-usage resource identified; automated web access was denied by robots.txt. No usage query completed here.

Resource discovery alone is not completed passage research. The completed Adelung work is described above; the correspondence, Grimm and DTA limits remain as recorded. The original pilot and historical method-review artifact remain preserved. Subsequent bounded authorizations and completed opening cycles are recorded in [DECISIONS.md](../DECISIONS.md); their completion does not certify German fidelity or resolve D001. The implemented database and its current scope are documented in the [v2 store guide](preparation/v2/store-guide.md).
