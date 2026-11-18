# Vocabulary comparison and audit

Humboldt’s printed division runs from the heading *β. Wörtervorrath.* to the end of passage 126 on pp. 410–444 in the 1906 edition. The [source record](source.json) links the printed, PDF and scan coordinates and keeps the ten historical notes at their original anchors. The [print checks](source-checks.json) record the OCR corrections and four readings checked again after the independent packet was frozen.

## Drafts and synthesis

Three translators received the complete German division and the whole work as explicitly uncorrected context. They produced all 368 renderings independently in three consecutive output blocks. The candidate prompts supply the same German source and task instructions to each translator. [Model runs](model-runs.json) identify the successful providers and prompt hashes.

The synthesis uses the Sol candidate as a base. The [comparison of changed readings](synthesis-changes.json) gives the local German, the three English alternatives and the rationale for each change. It draws on the earlier division, the local [terminology controls](term-controls.json) and the argument across the whole section. The [chosen correspondences](decisions.json) record selected word and phrase alignments.

## Audits and revision

Astra and Muse each checked every block of the same frozen synthesis against the German. [Audit results](audits.json) retain all 107 individual findings and their dispositions. The [revision record](revision-changes.json) gives each changed rendering. The reading preserves apparent problems in the print and makes consequential English choices explicit in the notes.

## Reading and inspection

The [complete reading](reading.md) contains one Arabic sequence for six notes by Humboldt, four by the 1906 editor and six by the translator. The heading’s publication note is attached to the heading. The local terminology guide explains nine recurring distinctions. The [source-unit map](source-unit-map.json) identifies the exact source and English versions for each rendering.

The edition dataset contains checked German, the three candidates, the synthesis and the revised English. Use `./humboldt passage 99` to inspect the versions, or trace one of the phrase correspondences listed in the decision record. The text follows the provisional printed base. Manuscript collation and specialist human fidelity review remain outstanding.
