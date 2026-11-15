# Contributing

Start with [the current edition guide](docs/architecture/user-guide.md), [translation policy](docs/preparation/translation-policy.md) and [licensing notice](NOTICE.md). `AGENTS.md` is preserved from the initial setup; its descriptions of absent software are historical. The current guide and handoff describe the implemented project.

Use Python 3.11 or newer. Run `./humboldt test` for synthetic, generated and real-corpus regression checks. `./humboldt test --legacy` additionally requires local source holdings and historical snapshots. Run `./humboldt validate` before proposing data changes; available original attachments can be checked with `--sources`.

Keep source transcription, proposed analysis, English alternatives, editorial commentary and verification status distinct. Check a new source passage against its scan. Cite the printed page, PDF page and scan leaf separately. Consult the conditional termbase rather than imposing one English equivalent per German word. English readability feedback does not establish German fidelity.

For record corrections, download a proposal draft through the reader or use the CLI. Include a reason and existing evidence IDs where applicable. Send drafts to the maintainer; one authoritative copy appends the journal. Do not merge independent journal files or edit/renumber old events. New passages and reviewed apparatus are imported as data. Text corrections create new versions and preserve old readings and links.

Keep code changes focused and add a regression case for substantive behavior changes. Use descriptive, imperative commit subjects. Pull requests should explain affected passages or records, the reason for a change, checks performed and remaining uncertainty. Preserve original IDs, source fingerprints, earlier decisions and historical artifacts.

Original code contributions use MIT; original translation/editorial contributions use CC BY 4.0. Identify any third-party material and its source/rights separately. Do not include credentials, library-access downloads, restricted data or private correspondence. Nothing in a contribution should silently upgrade an OCR reading, model judgment or provisional interpretation to specialist validation.
