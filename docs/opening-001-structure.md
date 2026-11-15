# Opening §1: structural preparation
<!-- SUMMARY: Preserved source-only sentence/clause preparation; later opening cycles and cumulative store linked below · status: historical proposed analysis · updated: 2026-11-15 -->

**Supersession notice — 15 November 2026:** this source-only structural report records the 14 November packet. Its grammatical alternatives remain proposed annotations. The statements below that no English comparison/audit has occurred describe that stage; the later [§1 cycle](../translations/opening-001/comparison.md), [§2 cycle](../translations/paragraph-002/comparison.md) and [reassessment](preparation/reassessment-001-002.md) are now complete. The [current SQLite store](preparation/v2/store-guide.md) preserves the earlier source packet alongside subsequent English versions and alignments. The original pilot remains unchanged; D001’s reported-cancellation qualification is still unresolved. The historical body is preserved.

## Source and status

**Provisional source status:** follows GS V (Leitzmann 1906), §1, printed pp. 364–365 / PDF 374–375. Drechsel (2024:155) reports cancellation of the first seven paragraphs. Manuscript marks, extent and editorial meaning remain unverified. The printed opening is retained under [D001](../DECISIONS.md); authorial finality is unresolved.

The [structured source packet](../sources/annotations/opening-001.json) contains the complete checked German §1, seven sentence spans, proposed grammatical annotations, and a three-sentence excerpt from the parallel *Untersuchungen*. It contains no English translation candidate. Spelling and punctuation are preserved; line-end hyphens are rejoined and the page break becomes a space. The section marker is stored in the label rather than the running text. The German body has 1,833 Unicode code points and UTF-8 SHA-256 `a2565fa80ff79414cd2cdf5ecce92753e6badb0fbd1aba4a31a078ccf8815be5`.

## Sentence map

The English descriptions are analytical summaries, not sentence translations.

| ID / opening words | Function and dependency to preserve |
| --- | --- |
| s1 — *Wenn es vielleicht sonderbar scheint* | Frames the geographical grouping as initially surprising, then offers its justification. Preserve the relation between the *wenn* clause, infinitival complement and *so* matrix. |
| s2 — *In Europa, Asien und Afrika* | Connects linguistic mixture to the lack of a linguistic reason for studying the languages in their present continental grouping. The relative clause belongs with *Verbindung*. |
| s3 — *Auch zeigen die Sprachstämme* | Adds differences of structure and attained *Bildung*. The referent of *eines jeden* and the rendering of *Bildung* need contextual judgment. |
| s4 — *Amerika dagegen hat* | Contrasts America, sets aside recent European immigration, then permits either no earlier immigration or only immigration leaving barely a historical trace. Both relative clauses and the elliptical *keine / solche* need explicit tracking. |
| s5 — *Welches daher auch der Ursprung* | Leaves origins open while asserting centuries of development through the peoples themselves and contact among them. Preserve that uncertainty and internal contact. |
| s6 — *Die unübersehbare Menge* | One written subject is shared by two coordinated predicates: *sind … gerathen* and *haben … mitgetheilt*. The temporal qualification and the scope of *nur* require care. |
| s7 — *Was daher auch in noch früherer Zeit* | Whatever may have entered earlier is said to undergo the levelling influence of restricted internal contact. The database records competing grammatical analyses of the initial constituent. |

## Analysis provenance and unresolved points

Claude **claude-fable-5-2** returned 20 proposed segments from the German alone: clauses, two predicate conjuncts and one predicative phrase. The coordinator checked every quoted span and parent containment mechanically. Those checks establish textual anchoring, not grammatical correctness. All analyses remain **proposed**.

For s7, analysis A treats the initial constituent as a free-relative subject. Analysis B records Claude’s mentioned alternative: a concessive adjunct with an unexpressed matrix subject. B is a coordinator-recorded alternative, not an independent second model endorsement. Its equal plausibility has not been established.

The p. 365 image confirms both the singular-headed *Menge* with plural *sind / haben* and the spelling *Europaeische*. These were flagged by Claude and rechecked; neither was silently corrected. The marginal **2** follows *einheimischen Verkehrs erfahren*, confirming the §1 boundary.

Other unresolved points include conditional/concessive force in s1, *wenigstens* scope in s2, *nur* scope in s5–6, the attachment and temporal/exceptive reading of *bis auf* in s6, and *diesen abschleifenden Einfluss* in s7. They are reasons for targeted comparison, not blanks to fill by model agreement. No dictionary or manuscript evidence was added overnight.

## What the store demonstrates

The example query follows **Sprachkunde → s2 → §1 → source-status evidence → D001**. These evidence and decision links apply to the containing paragraph; they do not supply a dictionary definition for *Sprachkunde*. A separate alignment links the two written tokens *keine Veranlassung* to their counterparts in the parallel excerpt. It records form correspondence, without asserting translation equivalence or manuscript chronology.

No English fidelity audit or candidate comparison has been performed. The old pilot and the pending workflow-review file remain unchanged. See [the prototype note](alignment-store-proposal.md) for the implementation and integrity checks.
