# Overnight preparation for review
<!-- SUMMARY: Preserved overnight review and historical next-step recommendation; later opening cycles and v2 preparation complete · status: historical review record · updated: 2026-11-15 -->

**Supersession notice — 15 November 2026:** this report preserves the overnight result and recommendation as presented. [D002](../DECISIONS.md) records Brett’s later “looks good. Carry on.” as authorization for the bounded §1 cycle; [D004](../DECISIONS.md#d004--1-english-review-complete-2-cycle-authorized-15-november-2026) records the completed §1 English review and §2 authorization. Both comparison/audit cycles and the later [§§1–2 reassessment](preparation/reassessment-001-002.md) are complete. The original method-review file remains an unchanged historical artifact, not an outstanding prerequisite for those completed actions. No Roughdraft completion event is invented for this overnight note or the old method wait. Current terminology and database status are in the [v2 coverage report](preparation/v2/coverage-report.md) and [store guide](preparation/v2/store-guide.md); older pending language and counts below describe the earlier stage.

## Result

The preparation now has three concrete pieces: a map of the printed work, a source-only structural packet for the opening, and a small working database. The database makes your requested links between words, clauses, sentences, paragraphs, evidence and decisions inspectable. You do not need to assess German fidelity to review whether those links and their displayed uncertainty are useful.

The English pilot and the pending working-method proposal remain unchanged. No new translation passage was drafted. D001 remains the source policy: retain the 1906 printed opening with the reported cancellation flagged, while authorial finality remains unresolved.

## What is ready

| Artifact | What it provides | Limit |
| --- | --- | --- |
| [Navigation map](work-outline.md) | Printed hierarchy, section/page links, sampled argument landmarks, and a distinction between surviving text and bracketed contents entries. | Contents-based orientation, not a full close reading of §§1–149. |
| [Opening structure](opening-001-structure.md) | Seven-sentence map, proposed clauses, unresolved scope/attachment questions, and provenance. | Mechanically checked anchoring does not certify the grammatical analysis. |
| [Linked-text prototype](alignment-store-proposal.md) | Runnable SQLite store, reusable source packet, queries, schema and tests. | Disposable prototype; adoption into the translation method awaits review. |

## A concrete database example

The store follows **Sprachkunde → sentence 2 → paragraph §1 → E01 (reported cancellation) → D001 (printed-base policy)**. The evidence and policy attach to the paragraph: this is a route to its source status, not a dictionary definition of the word.

Two grammatical analyses of sentence 7 coexist without changing a character of the German. One treats the opening constituent as a subject free relative; the other records a possible concessive-adjunct analysis. Neither is marked approved. A separate group links the two words *keine Veranlassung* to their two counterparts in the parallel German fragment. Alignment groups can therefore hold several units on each side.

The current database has **2 text versions, 4 analyses, 376 units, 4 evidence records, 1 decision and 1 alignment group**. All **15 software tests pass**. SQLite’s integrity check returns `ok`, with no foreign-key errors. Tests include exact span recovery, Unicode offsets, source fingerprints and rejection of invalid spans, parents, mutations and incomplete alignments. They do not test translation quality.

## Consultation and checks

Claude **claude-fable-5-2** proposed 20 German segments from the supplied source alone. I checked the exact spans, retained its uncertainty notes, and separately recorded the sentence-7 alternative. Muse **muse-wonder-full-1.0** critiqued the design. I adopted its smaller scope and the separation between checked quotations and unverified underlying claims. Both calls completed normally; their agreement is not independent source verification.

The p. 365 image confirms the printed singular-headed *Menge* with plural predicates and the spelling *Europaeische*. The source packet preserves both. A larger check of the parallel opening corrected my initial transcription *besondere* to printed *besondre* before the final database was built. The map also records *Wortvorrath* in the contents versus *Wörtervorrath* in the body heading.

No dictionary evidence, manuscript evidence or additional acquired reference was added overnight. The cancellation report remains checked as Drechsel’s statement, not as a manuscript finding.

## Recommended next step

Keep this database as the trial design for the opening, then resolve the separate [working-method review](WORKFLOW-REVIEW.md) before running the proposed independent English-candidate comparison and audit. The useful review decision here is whether the linked records and separate statuses meet your needs; it is not a request for you to certify German or approve the existing English.

The implementation, inputs, verification record and worker receipts are saved locally. No dependency was installed, purchase or external message made, or repository change committed or pushed. This note is the single new Roughdraft review target. Further source retrieval, production database adoption and translation extension remain separate tasks.
