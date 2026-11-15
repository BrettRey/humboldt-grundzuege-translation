# Verification of the architecture corrections

Completed on 15 November 2026 under D013, using Python 3.14.10. Engine version **0.2.0** fixes the confirmed correction-workflow defects from [Fable’s review](reviews/claude-fable-20261115T204942Z/checked-findings.md). [Machine-readable evidence](correction-verification.json) records hashes, test counts and portable commands. The original review and release 0.1.0 remain preserved.

## Findings and remedies

| Finding | Result |
| --- | --- |
| Corrected texts lose section membership or cannot receive apparatus | Fixed. Membership follows recorded version ancestry. Explicit `requires_versions` dependencies materialize reviewed layouts/alignments during replay; later proposals can amend that apparatus. Predecessor/successor navigation is available. The complete lifecycle also passes in a portable fixture release. |
| Unrelated base metadata changes block historical replay | Fixed for new format 2 events. Fingerprinted observed rows remain stored; historical context drift is visible as a review impact. Original-value conflicts still fail, and full-row stale checks protect pending acceptance. Format 1 retains its original checks. |
| Ordinary metadata/rendering/form edits bypass history | The attributed path now covers these records, evidence descriptions/status, decisions and alignment members. Composite JSON keys identify records without an `id` column. Invalid relational amendments cannot publish accepted decisions. Text bodies still create new versions. |
| CRLF creates false changes and breaks paragraph splitting | Fixed. Authoring normalizes line endings, no-op proposals fail, and historical CRLF paragraph spans are recognized without changing old bodies. HTTP regression exercises the form boundary. |
| Independently authored journal branches cannot merge | The current single-writer constraint is explicit in the guide and error messages. Contributors exchange fingerprinted drafts. No distributed reconciliation algorithm or implicit renumbering was introduced. |
| Evidence form wording and unavailable translation attachments | Fixed. Forms request existing evidence IDs, with a documented evidence-dataset route. Declared/linked translation files use the same confinement protections as source attachments; unlisted paths remain blocked and active formats download safely. |
| Storage defence/schema duplication | Retained as a proportionate design choice. A consistency test compares all 33 scholarly JSON table column sets with SQL. The migration command is documented as an advanced operation, outside normal rebuilds. |
| No routine real-data regression; recovery/filesystem guidance | A frozen initial-manifest baseline now runs in the default suite. Explicit `verify --against` comparisons distinguish initial base records from complete later releases. Locks and hard-link requirements have actionable guidance; unsupported authoring filesystems fail safely. |

## Verification evidence

**122 tests pass:** 59 unit tests, 19 integration/workflow tests, one real-corpus regression and 43 historical tests. Final unit/integration/corpus logs and the unchanged historical suite are recorded separately. The current suites emit no resource warnings; preserved historical tests retain their earlier connection warnings.

Generated checks compare 40 sequences of 30 operations with an independent small state model, including stale acceptance, rejection, deterministic replay and input preservation. Twelve successive generated text edits check retention of every previous body and semantic link. These tests are evidence over exercised cases, not a proof over all possible executions.

All **33 original scholarly tables match row-for-row**, retaining the logical digest `53334ec49b583ad5538bb21d17249eb8416c38adb14b44874d6ac5027a83a962`. All **118 protected files** match the migration baseline. There are zero real editorial journal events: only temporary synthetic editions were amended during testing. No German or English text changed.

Both frozen releases pass every listed file hash: 27 files in 0.1.0 and 30 in 0.2.0. The 0.2.0 package matches the final engine and includes its guides and baseline. A clean copy of its code/data validates, rebuilds, searches and traces with socket connections disabled, a minimal environment and no original sources, legacy tools, translations, tests or `tmp/`. It yields the same logical identity. Seven live reader routes return HTTP 200, including the new rendering-record page and a declared translation attachment; the final term page was visually inspected in a fresh headless browser profile.

## Scope and remaining limits

No Lean dependency or proof job was added. [The journal contract](journal-contract.md) explains where a future proof might help and why it would need a connection to executable behavior. Python 3.11+ is declared; only Python 3.14.10 was exercised here. FAT/exFAT authoring remains unsupported. The journal has one authoritative writer; it is not a multi-writer merge protocol. Attribution remains a recorded claim, and semantic reattachment still requires review.

The repository remains uncommitted under the earlier explicit boundary. New local release snapshots and append-only amendments preserve the implemented working history; a Git baseline remains a separate repository-management action. No publication, additional translation or specialist fidelity validation occurred. See the [current guide](user-guide.md) for the supported operations.
