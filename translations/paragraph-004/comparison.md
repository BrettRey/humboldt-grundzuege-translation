# §4 comparison and audit dispositions

## Source and scope

Three complete source sentences were compared with GS V (Leitzmann 1906), printed366 / PDF376 / scan leaf378, from marginal4 to before marginal5. Line-end word divisions are joined. There is no source or editorial footnote within this paragraph. The [source record](source.json) preserves the German and fingerprints; the [packet](packet.md) includes only German context and source metadata.

D001 remains binding: Drechsel (2024:155) reports cancellation of §§1–7; manuscript marks, extent and editorial meaning remain independently unverified. This translation retains the printed reading without settling authorial finality.

## Independent comparison

Three isolated candidates completed, using runtime identities `claude-fable-5-2`, `muse-wonder-full-1.0` and `gpt-6.1-sol`. Each received the same source-only packet without earlier English, glossary answers or the other candidates. [Their complete drafts and notes](candidates.md) were frozen before synthesis. The coordinator then consulted the relevant termbase rules and prepared the [pre-audit synthesis](synthesis.json).

Two fresh audits, Fable and Muse, each covered all three source sentences against the supplied German. Neither received candidates, termbase answers or the other audit. Both found no material defect and raised seven minor findings in total. Their judgments are retained in [audits.json](audits.json), with a disposition for every finding. The final revision received a coordinator source/terminology check; no further independent model round is claimed.

## Local decisions

- **Publication order:** the alternative plans put either individual grammars/dictionaries or general conclusions first. The latter and former references retain that order. Conclusions (*Folgerungen*) and claims (*Behauptungen*) remain distinct. “The research” restores the source’s definiteness without adding a possessor.
- **Verification resources:** *der vorhandenen* refers to existing resources. The final colon explicitly connects their inadequacy with the reader’s restricted checking. “Only very incompletely” preserves the extent of verification; the statement does not imply total inability.
- **Unrealized delay:** the protracted undertaking and the time that would necessarily have elapsed remain coordinated deterrents. Publication difficulty belongs inside the time clause. The hypothetical delay is not described as an actual elapsed period. *Herausgabe* is provisionally “publishing”; editing/bringing out remains possible.

The two selected term-rule links are `lex:darstellung:s01` (presentation versus empirical research order) and `lex:huelfsmittel:s01` (resources for studying/checking individual languages). They are contextual associations, not exhaustive sense coding. Existing termbase entries and earlier English are unchanged.

## Audit dispositions

| Audit | Finding | Disposition |
|---|---|---|
| claude | F1 (p4:s2) | Join the English blocks with a colon so the need to create resources explicitly explains the limited checking within the stated disadvantage. Preserve the beneficiary through singular they referring to the reader. |
| claude | F2 (p4:s2) | Remove the added needed; replace imperfectly with incompletely to retain extent. Use given for bei, rarity for Seltenheit and those that exist for the existing resources. |
| claude | F3 (p4:s1) | Restore the definite the research, referring to the investigations underlying these conclusions, without inserting a possessor. |
| claude | F4 (p4:s3) | Restore time elapsing in the process and place the publication-difficulty adjunct inside its relative clause. Necessarily and would have preserve the modal and unrealized temporal relation without implying that the delay actually occurred. |
| muse | F1 (p4:s2) | Use an explanatory colon joining the limited checking and resource need; the relation is explicit rather than left to sentence juxtaposition. |
| muse | F2 (p4:s2) | Use only very incompletely, preserving the completeness limitation rather than a claim that the checking is defective. |
| muse | F3 (p4:s2) | Use those that exist, referring to resources; avoid a suggestion of ready availability. Retain rarity and inconvenient arrangement. |

## Edition and verification

The generic dataset `passage-0004` preserves six text versions, sentence/rendering blocks, Unicode word units, ten consequential source/English span correspondences, primary sentence evidence, two audit records and linked decisions. The revised English is a reading default, with every alternative retained. No permanent passage-specific builder or engine change was added.

The [verification record](verification.json) checks the initial baseline, all 118 protected files and previous scholarly rows. The sole prior-row amendment records Brett’s completed §3 English-readability feedback in provenance; its body remains identical and its former metadata remains in the journal. The engine conservatively flags 198 linked §3 records for interpretation review after this metadata change; those flags are retained.

All 125 local tests pass, including 43 historical checks; source fingerprints, integrity and foreign keys pass. Software checks establish record properties, not German fidelity. English/editorial review of §4 remains pending, and no specialist human validation or general error-rate estimate is claimed. Stop before §5.
