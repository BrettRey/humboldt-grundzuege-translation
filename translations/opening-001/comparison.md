# Clause comparison and decision record

<!-- SUMMARY: All 20 proposed anchors and 12 audit findings accounted for; choices remain provisional · status: one cycle complete · updated: 2026-11-15 -->

## Method and provenance

The [packet](packet.md) was supplied without the old English or earlier proposed term renderings to three fresh CLI sessions. Actual runtime models were Claude `claude-fable-5-2`, Muse `muse-wonder-full-1.0`, and OpenAI `gpt-6.1-sol`. All returned normally and covered all seven source sentences. The frozen [candidates](candidates.md) were saved before the coordinator revealed the old pilot. They are model proposals from a common input, not three independently established readings of a manuscript.

A coordinator synthesis was then audited in two fresh sessions, with no other candidate or audit provided. The complete pre-audit text, findings and seven-sentence coverage records are preserved in [audits.json](audits.json). Only one audit/revision cycle was run.

## Consequential differences

| Question | Candidates and source-based choice |
| --- | --- |
| *Welttheil* | Claude/Muse use “part of the world”; OpenAI uses “continent”. Retain continent locally, with America treated as one unit and the historical scope noted. |
| *Bildung* | All propose development, while retaining formation/cultivation as alternatives. The grammatical referent is linguistic; agreement does not settle the term across the work. |
| Distinctiveness | Claude uses individuality/individualities; Muse distinctiveness/peculiarities; OpenAI character/characteristics. Related distinctive wording retains the link without implying oddity or fixing a theory of inner form. |
| Sentence 6 | Claude/Muse keep the peoples entering ferment; OpenAI makes powers the subject of a passive. The pre-audit synthesis used that passive; audits led back to the source subject and intransitive relation. |
| *abschleifend* | Abrading (Claude), smoothing (Muse), wearing-down (OpenAI). Final wearing-down preserves the process without asserting equalisation; levelling remains an alternative. |

## Source coverage

Anchors overlap because matrix spans include dependent material. Coverage means that an English rendering and a decision can be retrieved; it does not prove semantic adequacy. The two alternative s7 analyses describe the same source constituent and are not counted as extra text. Exact source/target spans are stored in [alignments.json](alignments.json) and the linked database.

| Source anchor | Treatment |
| --- | --- |
| `a:s1c1` | Conditional frame and both grounds retained. |
| `a:s1c2` | Conditional remains tentative; stronger concessive Although not adopted. |
| `a:s1c3` | Infinitival content retained. |
| `a:s2c1` | Converged avoids claiming language mixture where the print describes confluence. |
| `a:s2c2` | At least and no reason retained. |
| `a:s2c3` | Object and grouping retained; no genealogy inferred. |
| `a:s2c4` | Chance qualification remains inside the grouping relation. |
| `a:s3c1` | Continental antecedent explicit; language stocks distinguished from human tribes; Bildung provisional. |
| `a:s4c1` | European exception, no/only immigration alternatives and America contrast retained. |
| `a:s4c2` | Destructive influence remains the only mode of effect; national vocabulary retained. |
| `a:s4c3` | Scarcely and qualification could be called historical retained. |
| `a:s5c1` | Centuries, internal determination and mutual contact retained; added activity noun removed. |
| `a:s5c2` | Origins remain open; both peoples and languages retained. |
| `a:s6c1` | Human groups remain subject of entry into ferment; English split into two sentences. |
| `a:s6c2` | One German predicate maps to two separated English spans; temporal qualifier moved before the subject. |
| `a:s6c3` | Repeated English subject makes shared German subject explicit; reciprocal and only retained. |
| `a:s6c4` | Knowledge limits the historical interval; no claim of complete prehistoric knowledge. |
| `a:s6c5` | Predicative adjunct remains within the ferment clause, not a new independent freedom assertion. |
| `a:s7c1` | Wearing-down retains abrasion metaphor; self-contained native interaction retains native/foreign opposition. |
| `a:s7c2` | Broad singular indefinite and modal preserved without specifying discrete linguistic elements. |

## Audit dispositions

Claude reported no material defects and seven minor/open findings. Muse reported three material findings and two minor/open findings. Both objected to the added activity noun and to aspects of the final sentence; their severity judgments differ. The coordinator used the exact German rather than a vote. The final version was checked against those findings, not submitted for another model approval.

| Audit finding | Disposition | Reason |
| --- | --- | --- |
| claude F1 | addressed | Restructured s6: qualifier attaches to entry into ferment; removed separate freedom assertion and added Over that period bridge. |
| claude F2 | partly accepted; alternative open | Retain temporal reading; use subjugation by Europeans; record exceptive alternative. |
| claude F3 | accepted | Removed activity and passive; retained self-relation in different idiomatic English forms. |
| claude F4 | accepted | Restore native/foreign opposition and distinguish interaction from contact; no continent noun in the English s7. |
| claude F5 | accepted | Use wearing-down; retain levelling as an alternative, not asserted result. |
| claude F6 | accepted | Mingled becomes converged; avoid suggesting linguistic mixture. |
| claude F7 | not accepted | Retain very considerable as an absolute/elative superlative; no comparison set is given. Muse explicitly finds it defensible. This is grammatical adjudication, not majority voting. |
| muse F1 | accepted | Removed activity noun in s5 and s6. |
| muse F2 | accepted | Keep human groups as subject of intransitive came into; freedom is an adjunct. |
| muse F3 | accepted conservatively | Wearing-down preserves metaphor; levelling remains a plausible interpretation rather than a demonstrated error. |
| muse F4 | accepted | Remove continent referent; retain reflexive internal interaction, native contrast and distinct Verkehr rendering. |
| muse F5 | accepted | Anything foreign preserves open singular scope; no elements noun. |

## Local terminology register

### D003.1 — Welttheil; Sprachkunde

**Working choice:** continent; study of language. Readable geographical/disciplinary expressions; America remains the single unit used in this passage, not a modern two-continent classification. **Alternatives:** part of the world; linguistic scholarship.

### D003.2 — zusammengeflossen; bedeutendsten; Sprachstämme; Bildung

**Working choice:** converged; very considerable; language stocks; development. Convergence does not assert mixing; absolute/elative superlative does not require a formal ranking. The grammar makes the stocks and attained Bildung linguistic. No modern genealogical rank or universal Bildung equivalent is asserted. **Alternatives:** flowed together; the most significant differences; language families; cultivation.

### D003.3 — Nationaleigenthümlichkeit; Eigenthümlichkeiten; Einwanderungen

**Working choice:** national distinctiveness; distinctive traits; immigration (mass noun). Related distinctive vocabulary preserves the conceptual connection; retain national without equating it with a nation-state. Mass immigration covers the plural events and supplies the repeated elliptical noun. **Alternatives:** national individuality / individualities; inner national character; immigrations.

### D003.4 — nur durch sich selbst; in Gährung ihrer Kräfte gerathen

**Working choice:** solely from within / through themselves alone; came into a ferment of their powers. Remove added activity noun and causative passive. Keep the peoples as the subject entering the state. Different English phrasing expresses the repeated self-relation without imposing one awkward formula. **Alternatives:** only through themselves in both clauses; their powers were set fermenting solely from within.

### D003.5 — solange ... kennen; bis auf ... Unterjochung; frei von fremdem Einfluss

**Working choice:** known historical interval; down to subjugation by Europeans; freedom as an adjunct. Temporal reading of bis auf is retained alongside the knowledge limit. The exceptive reading remains possible. Keep the freedom phrase within the entry-into-ferment clause; the second predicate follows in a new English sentence without adding a new temporal bridge. **Alternatives:** except for European subjugation.

### D003.6 — abschleifend; einheimischer Verkehr; Fremdes

**Working choice:** wearing-down; self-contained native interaction; anything foreign. Retain abrasion rather than making equalisation the asserted outcome. Interaction differs from contact in s5; native contrasts with foreign. The reflexive stays with the interaction, not an inserted continent noun. Self-contained is understood here at the passage’s collective level, not as isolation of each community. Anything foreign avoids narrowing to discrete linguistic elements. **Alternatives:** levelling; smoothing; native intercourse confined to itself; whatever foreign matter.

## Old pilot comparison and remaining limits

The original pilot remains byte-for-byte unchanged. This version uses a tentative “If” rather than the stronger “Although”, narrows the confluence wording to “converged”, makes the continental antecedent explicit in s3, and revises s6’s subject/voice and s7’s reflexive/native contrast. It does not add a title translation. These are supported local choices, not a retrospective fidelity approval of the old pilot.

No historical dictionary entry was successfully retrieved in the bounded lookup. One search returned portals rather than entries; direct Adelung and DWDS entry fetches failed. No dictionary definition was used to settle a choice. No broader retrieval or manuscript investigation was undertaken in this cycle. Existing contextual reading is documented in the [evidence note](../../docs/opening-001-evidence.md), with its limits.

The authorial-cancellation report, wider term consistency, temporal/exceptive bis auf, and the best English form of the ferment metaphor remain open. The final revision is a provisional research translation with model audits, not qualified human certification. Stop at this paragraph; later passages require a new bounded task.
