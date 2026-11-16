# Humboldt: Grundzüge des allgemeinen Sprachtypus
<!-- SUMMARY: Complete Introduction assembled and audited by section · status: full Introduction and §147 English review pending · updated: 2026-11-15 -->

Software is available under [MIT](LICENSE); original translation and editorial content use [CC BY 4.0](LICENSE-CONTENT), with [public-domain and third-party exclusions](NOTICE.md). See [CONTRIBUTING.md](CONTRIBUTING.md) for the current contributor workflow. This is an AI-assisted provisional research translation; its source and validation limits remain explicit below.

The [public repository](https://github.com/BrettRey/humboldt-grundzuege-translation) is live on `main`. [GitHub CI](https://github.com/BrettRey/humboldt-grundzuege-translation/actions/workflows/tests.yml) runs the default checks on Python 3.11 and 3.14.

The complete [Introduction, numbered passages1–7](translations/introduction/revised.md), is ready for English review as one editorial unit. [Its comparison](translations/introduction/comparison.md) records three source-only candidates for the new6–7 translation, two fresh audits covering all38 section sentences, and27 dispositions. Whole-work German OCR was supplied as labelled background. Two source-based clarifications in1 and4 use new versions; every earlier body remains available. The reported cancellation status remains explicit. See the [workflow by section](docs/translation-workflow.md); numbered passages retain precise citation IDs, while production and human review follow the printed sections.

The edition now has a shared Python engine, durable record bundles and a local reader. Start with the [user and contributor guide](docs/architecture/user-guide.md) to build, search, follow word/span evidence, propose corrections or add another passage as data. The [data contract](docs/architecture/data-contract.md) explains permanent IDs, versions and revision history; the [verification report](docs/architecture/verification.md) records preservation and portability checks. Historical builders and snapshots remain available for reproduction.

[Claude Fable’s architecture review](docs/architecture/reviews/claude-fable-20261115T204942Z/checked-findings.md) prompted the [verified correction-workflow fixes in 0.2.0](docs/architecture/correction-verification.md): dependent apparatus for corrected versions, section ancestry, metadata history, line-ending handling, safe translation attachments and a real-corpus regression. The journal has one authoritative writer; contributors exchange drafts. Lean was assessed and deferred as disproportionate to the current need.

The [representative difficult pilot, §147](translations/difficult-147/revised.md), is complete through one comparison/audit/revision cycle. It tests dense conceptual syntax, word order and a historical Chinese example; [the assessment](translations/difficult-147/comparison.md) records what the workflow caught and what remains uncertain. English review is pending. [Textual-basis options](docs/preparation/textual-basis-options.md) explain how to proceed with the declared 1906 base while the 2017 edition remains unacquired.

This project prepares a provisional English translation of Wilhelm von Humboldt’s *Grundzüge des allgemeinen Sprachtypus*. The [individual termbase](docs/preparation/termbase.md) now contains 1,048 headword records with local evidence, conditional English choices and explicit relations. All 110 main-text pages and all 3,515 discovery candidates have terminology-review dispositions. The [coverage report](docs/preparation/v2/coverage-report.md) defines the completed preparation and its limits; the earlier 34-group register is preserved as history. Existing §§1–2 remain unchanged after [reassessment](docs/preparation/reassessment-001-002.md). Brett waived Roughdraft for that preparatory stage; the subsequent passage cycles are recorded separately above. See the [handoff](docs/HANDOFF.md) before continuing.

Preparatory work produced a [navigation map](docs/work-outline.md), [opening structural packet](docs/opening-001-structure.md), and tested [SQLite prototype](docs/alignment-store-proposal.md). The [overnight review](docs/overnight-review.md) records what Brett approved. The earlier method proposal remains unchanged as a historical artifact; D002 and D004 record the bounded authorizations. The [§1 comparison](translations/opening-001/comparison.md) and [§2 comparison](translations/paragraph-002/comparison.md) document their decisions and limits.

## Source

The source is *Gesammelte Schriften*, volume V, edited by Albert Leitzmann (Berlin: B. Behr’s Verlag, 1906), from the [University of Toronto scan at the Internet Archive](https://archive.org/details/gesammelteschrif05humbuoft). The volume and editor title pages are PDF pages 6 and 7.

The main text occupies printed pages 364–473 (PDF pages 374–483), followed by contents on printed pages 474–475 (PDF pages 484–485). Small-print editorial notes are distinct from Humboldt’s text. [The source manifest](sources/manifest.json) records download URLs, edition details, file sizes, hashes, and verification limits.

[Decision D001](DECISIONS.md) retains the opening as printed in 1906. **Provisional source status:** Drechsel (2024:155) reports cancellation of the first seven paragraphs; the manuscript marks, extent and editorial meaning remain unverified. The existing §1 pilot follows the printed base text and remains an unvalidated draft. Every subsequent draft or export of the opening must carry this source-status note.

## Files

- `src/humboldt/`: the shared engine, CLI, reader, packaged SQL migrations and record schemas.
- `edition/`: authoritative record bundles, manifest and append-only correction journal; no dependency on ignored snapshots.
- `build/edition.sqlite`: generated current database; `releases/0.2.0/`: current local portable release; `releases/0.1.0/`: preserved initial release. Generated outputs are excluded from Git.
- [docs/architecture/user-guide.md](docs/architecture/user-guide.md): current build, query, revision, import and release instructions.
- [docs/preparation/README.md](docs/preparation/README.md): completed preparation, results and limits.
- [translations/difficult-147/revised.md](translations/difficult-147/revised.md): complete difficult pilot, English and separate source/translator notes.
- [translations/difficult-147/comparison.md](translations/difficult-147/comparison.md): three candidates, two separate audits, thirteen dispositions and pilot assessment.
- [translations/difficult-147/store-guide.md](translations/difficult-147/store-guide.md): preserved pilot-stage snapshot and historical reproduction instructions.
- [docs/preparation/termbase.md](docs/preparation/termbase.md): current alphabetical termbase, with individual records and checked source quotations.
- [docs/preparation/v2/coverage-report.md](docs/preparation/v2/coverage-report.md): selection method, all-page/candidate accounting, corrections and remaining limits.
- [docs/preparation/v2/store-guide.md](docs/preparation/v2/store-guide.md): preserved terminology-stage database, reproduction and queries.
- [docs/preparation/terminology-register.md](docs/preparation/terminology-register.md): preserved earlier 34-group discussion register; no longer the coverage claim.
- [docs/preparation/argument-map.md](docs/preparation/argument-map.md): continuous argument map of all 110 main-text pages.
- [docs/preparation/reading-ledger.md](docs/preparation/reading-ledger.md): exact reading/image coverage and unread material.
- [docs/preparation/store-guide.md](docs/preparation/store-guide.md): earlier discovery-store guide, retained for reproducibility.
- [AGENTS.md](AGENTS.md): contributor guidance, preserved from the initial setup. Its descriptions of absent Git and proposed paths reflect that earlier stage; this README and the handoff record the current state.
- [DECISIONS.md](DECISIONS.md): project-local editorial decisions, beginning with the provisional printed-base policy.
- [docs/HANDOFF.md](docs/HANDOFF.md): checked state, limits, and next step.
- [docs/CORPUS-STATUS.md](docs/CORPUS-STATUS.md): acquired references, historical-text locations, and item-specific access limits.
- [docs/reference-sections.md](docs/reference-sections.md): direct PDF/Markdown links and section coverage for Manchester and Drechsel.
- [docs/opening-001-evidence.md](docs/opening-001-evidence.md): focused reading note, parallel opening, unresolved textual status, and terminology candidates for §1.
- [docs/work-outline.md](docs/work-outline.md): contents-based navigation and sampled argument landmarks; not a full close reading.
- [docs/opening-001-structure.md](docs/opening-001-structure.md): seven-sentence map and proposed grammatical analyses.
- [docs/alignment-store-proposal.md](docs/alignment-store-proposal.md): prototype design, reproduction commands, checks and adoption limits.
- [sources/annotations/opening-001.json](sources/annotations/opening-001.json): exact German text, proposed annotations, evidence and policy records for the prototype.
- [docs/WORKFLOW-REVIEW.md](docs/WORKFLOW-REVIEW.md): recovered brief, resource assumptions, and proposed passage workflow.
- [docs/SETUP-REVIEW.md](docs/SETUP-REVIEW.md): setup proposal and authorization record.
- [sources/manifest.json](sources/manifest.json): source provenance and checksums.
- [sources/page-map.json](sources/page-map.json): printed page, PDF page, and scan leaf for every page of the work and its contents.
- [sources/grundzuege-ocr.txt](sources/grundzuege-ocr.txt): **uncorrected** extraction of the PDF’s embedded OCR, with page markers. Running heads and editorial notes remain in the extraction.
- [translations/pilot-001.md](translations/pilot-001.md): checked German, draft English, and separately labelled translator’s notes for the opening paragraph.
- [translations/opening-001/revised.md](translations/opening-001/revised.md): reviewed §1 English and editorial notes, preserved with the user’s approval comment.
- [translations/opening-001/comparison.md](translations/opening-001/comparison.md): all 20 proposed source anchors, 12 audit dispositions, local terminology choices and remaining limits.
- [translations/opening-001/candidates.md](translations/opening-001/candidates.md): three frozen fresh candidates; structured inputs, audits and provenance are alongside it.
- [translations/paragraph-002/revised.md](translations/paragraph-002/revised.md): preserved §2 English and editorial notes, retained after broader reassessment.
- [translations/paragraph-002/comparison.md](translations/paragraph-002/comparison.md): source checks, eleven anchor links, six audit dispositions and local term choices.

`sources/raw/` holds the original PDF, Archive OCR, and scan metadata. It is excluded from Git, as is `tmp/`. Embedded text, evidence and the reader work without those holdings; local PDF links require the attachments recorded in the manifests.

## Working locally

Use Python 3.11 or newer from the project root. Runtime dependencies are limited to the standard library; no installation or model credentials are needed:

```bash
./humboldt validate
./humboldt build
./humboldt search understanding
./humboldt trace 'difficult-147-de-v1:s05:w013'
./humboldt browse
./humboldt test
./humboldt test --legacy
```

Use `build --force` to replace a generated database under `build/`. The reader prints a loopback URL and opens no external service. Accepted corrections are recorded before rebuilding; text corrections create new versions and flag affected links. `import` adds a prepared passage dataset through the same engine. See the guide for exact commands and supported correction fields.

The current generated store is `build/edition.sqlite`: 53 text versions, 61 analyses, 94,821 units, 1,833 evidence records, 1,668 decisions and 374 alignment groups. Every row in the original 33 scholarly tables is preserved. The journal retains three English-review metadata amendments and two body revisions, with every earlier body and prior metadata preserved. Its 1,677 conservative review-impact records remain visible; new source correspondence is declared separately. It retains 1,048 headwords, 1,518 contextual sense/use groups, 1,531 local uses and 1,566 primary term attestations. Its authoritative inputs live in `edition/`, including numbered passages3–7 and147 plus the Introduction’s section records and clarification apparatus as generic datasets. `tmp/difficult-147/pilot.sqlite` and earlier snapshots are historical migration evidence, not prerequisites for normal builds.

The default tests use synthetic fixtures, generated transition checks and the real durable corpus; `--legacy` adds historical tests requiring original holdings and snapshots. Old builders remain under `tools/`. The [release command](docs/architecture/user-guide.md) builds a local runnable snapshot containing code, records, a sealed database, guides, licenses and a hash manifest. Generated release folders remain local rather than being committed. GitHub CI is configured to run the default checks on Python 3.11 and 3.14 after a push. Software checks establish storage, links and reproducibility, not semantic adequacy or certified lexical frequencies.

Compare source fingerprints with the manifest. Check each passage against the page image before translating. The page map is derived from scan metadata. The terminology readers report checking all main-text page images and selected quotations; this is model-assisted verification, not specialist human validation. The full OCR has not been corrected or proofread.

Use the individual termbase and source-image checks in the next authorized passage cycle. Brett’s English review cannot establish fidelity to German he does not read. Keep German, English, editorial apparatus, and translator’s commentary explicitly labelled. D014 authorizes the public Git repository; see the handoff for current commit/push status. The complete Introduction is the current English-review unit; the next production unit is the opening of Part I, numbered passages8–15.
