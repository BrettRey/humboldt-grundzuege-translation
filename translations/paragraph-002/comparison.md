# §2 comparison and decision record

<!-- SUMMARY: Eleven proposed source anchors and six audit findings accounted for · status: one cycle complete, interpretation provisional · updated: 2026-11-15 -->

## Source checks

The complete three-sentence paragraph is printed365 / PDF375 / scan leaf377, between marginal2 and marginal3. It has 756 Unicode code points and 102 whitespace-delimited written tokens. The image confirms Gränzen where embedded OCR has Grenzen, and singular erlaubt with Norden und Süden. Historical spelling/punctuation is retained; line-end hyphens are rejoined. [The source packet](packet.md) and [structured annotations](../../sources/annotations/paragraph-002.json) record the text and fingerprints.

The parallel at printed346/PDF356 was read and visually checked. It has Gleichartigkeit and a claim of common lack of alphabetic writing/literature, without this paragraph’s lower-level wording or its denial of deviation from all other languages. Its different wording is not merged into the base, and no revision chronology is inferred. Adjacent §1 closing sentences and §3’s opening supply primary context. No new modern reference, dictionary entry or manuscript evidence was consulted.

## Candidate comparison

Fresh isolated Claude claude-fable-5-2, Muse muse-wonder-full-1.0 and OpenAI gpt-6.1-sol calls completed successfully. All three covered g2:s1–s3 and received identical prompt hashes. No earlier §2 English draft existed when these candidates were requested; the reviewed §1 English was withheld from the candidate prompts. The coordinator used §1’s local choices only during synthesis, after candidate freezing.

| Choice | Alternatives and reason |
| --- | --- |
| Ausbildung | Cultivation (Claude) versus development (Muse/OpenAI). Retain development locally; the bearer here is nations, distinct from the language-related Bildung in §1. |
| in ihnen selbst | Claude/OpenAI name languages; Muse retains an awkward open pronoun. Keep readable explicit languages with the nations alternative noted, based on discourse/context rather than voting. |
| Einerleiheit | Sameness (Claude/OpenAI) versus uniformity (Muse). Keep sameness of structure, distinct from similarity, without equating this with identity of whole languages. |
| auch wohl | Candidates differ in supplying a second sometimes. Remove that extra frequency after audit and retain the disputed nuance in the notes. |
| erlaubt | Source singular is preserved in German; English plural do is idiomatic. Agreement alone does not justify a new collective interpretation. |

## Anchor coverage

Overlapping matrix/coordination anchors include dependent material. An exact target span establishes traceability, not semantic certification. All eleven anchors are mechanically anchored in the [alignment file](alignments.json) and cumulative database.

| Source anchor | Treatment |
| --- | --- |
| `p2:a:s1c1` | Further support retains the backward reference and additive discourse force, without inventing a named thesis. |
| `p2:a:s2c1` | Concessive contrast, certainly, lower evaluation and without exception retained. |
| `p2:a:s2c2` | Explicit languages resolves ihnen provisionally; alternative nations reading is recorded. |
| `p2:a:s2c3` | Languages belong to nations; nations are not silently redefined as nation-states. |
| `p2:a:s2c4` | Alphabetic and in the proper sense remain restrictive; all remains pronominal; evaluation not neutralized. |
| `p2:a:s3c1` | Both alleged features disappear; actual similarity is retained; northern/southern linguistic division is not made a genealogical claim. |
| `p2:a:s3c2` | It is true / Nevertheless retains zwar / aber across the English sentence split. |
| `p2:a:s3c3` | No second frequency adverb supplied for wohl; its modal/discourse nuance remains open. Wrongly qualifies only sameness. |
| `p2:a:s3c4` | In fact makes wirklich explicit; broad features of similarity is weaker than sameness. |
| `p2:a:s3c5` | Idiomatic English plural; retain in this respect without supplying a specific antecedent for darin. |
| `p2:a:s3c6` | The infinitive is recast passively; genuinely qualifies separating boundaries, not a claim of national borders. |

## Audit dispositions

Two fresh Claude/Muse sessions audited the synthesis without another candidate or audit. Both reported no material semantic error, with six formal minor/open findings in total. That is model judgment from the supplied packet, not independent source verification. [The audit record](audits.json) preserves the pre-revision text and complete findings. Claude’s return also self-reported a steering-file hook notice; that unexamined claim was not used as task evidence or authority.

| Finding | Disposition | Reason |
| --- | --- | --- |
| claude F1 | retain with note | Keep the defensible explicit languages reading and record the grammatically possible nations antecedent. |
| claude F2 | retain with note | Keep them all unexpanded; note that proximity to explicit languages tilts English anaphora without settling German alle. |
| claude F3 | retain with note | Retain even in this respect and record the unclear antecedent and focus; no extra geographical or genealogical claim. |
| claude F4 | accepted | Add in fact for wirklich; retain actual similarity versus wrongly asserted sameness. |
| muse F1 | accepted conservatively | Remove the second sometimes; retain also been asserted and log wohl as an unresolved modal/discourse nuance. |
| muse F2 | retain idiomatic agreement | Keep English plural do. A singular German verb is not sufficient evidence for importing the proposed continent-as-subject recast. |

## Local choices and remaining limits

### D005.1 — Dafür ... nun auch

**Choice:** Further support for this. Keep backward reference broad; do not replace it with a claim of common descent or a uniquely identified §1 thesis. **Alternatives:** now also speaks in favour of this.

### D005.2 — Ausbildung; in ihnen selbst; alle

**Choice:** development; in the languages themselves; them all. Languages is a defensible discourse/context reading of ihnen, not a grammatical proof. Nations remains a possible antecedent. Keep alle pronominal; the explicit earlier choice may tilt the English reader toward languages, a limitation recorded rather than hidden. Nations renders Nationen without an implied modern nation-state. **Alternatives:** cultivation; in the nations themselves; unmistakable within them as well.

### D005.3 — alphabetischer Schrift; eigentlicher Literatur; niedrigeren Stufe

**Choice:** alphabetic writing; literature in the proper sense; a lower level. Preserve both lexical restrictions, the asserted hence relation, without exception and lower comparative. This is Humboldt’s evaluation; no neutral or modern historical correction is silently substituted. The parallel lacks the lower-level phrase. **Alternatives:** literature proper; at a lower stage.

### D005.4 — Einerleiheit / Aehnlichkeit; Bau; auch wohl; wirklich

**Choice:** sameness / similarity; structure; also been asserted; in fact. Reject alleged sameness and alleged deviation from all other languages without losing retained similarity. Wrongly modifies only the first assertion. Do not repeat a frequency adverb for the second, where wohl is not clearly temporal. Restore explicit in fact. Structure remains consistent with §1, without fixing a universal glossary. **Alternatives:** uniformity / resemblance; also sometimes been asserted; also possibly asserted.

### D005.5 — Welttheil; erlaubt; nicht einmal darin; abscheidende Gränzen

**Choice:** continent; do not permit ... even in this respect; genuinely separating boundaries. Retain continent from §1 and idiomatic English plural agreement. The printed singular erlaubt is preserved in the German; it does not by itself establish an intended collective conceptual contrast. Keep darin’s reference open, rather than inserting a claim of a strict north/south genealogy or national border. **Alternatives:** part of the world; the continent, north and south, does not permit; truly dividing boundaries.

## Trial store and stopping rule

Build a fresh cumulative §1–§2 database with `python3 tools/build_paragraph_002.py --db tmp/a-fresh-name.sqlite`. The existing §1 snapshot and all sealed inputs are preserved. The new store adds §1’s bounded English-review approval separately from source-language certification, and retains all §2 candidates, audit text, revision, decisions and target spans.

This cycle ends at §2. Pronoun references, the nuances of wohl/darin and manuscript finality remain open. No further audit loop is justified merely by those uncertainties. Later paragraphs need a new instruction.
