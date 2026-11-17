# Developing web edition
<!-- SUMMARY: Static publication of the recorded translation on Brett's website · status: approved design implemented · updated: 2026-11-17 -->

The public reader lives at [brettreynolds.ca/humboldt/](https://brettreynolds.ca/humboldt/). It uses the existing website’s EB Garamond, small-cap headings, colour variables and theme control. English opens first; parallel German is optional. Each complete reading page has one Arabic note sequence across all three authorships.

## Refresh the reader

From this repository, with Python 3.11+ and the existing Pandoc executable:

```sh
python3 tools/export_website.py --output /path/to/website/humboldt
python3 tools/check_website.py --output /path/to/website/humboldt
node --test tests/website-reader.mjs
```

Hosting remains ordinary static GitHub Pages. The export requires no running Python service, database, account system or npm installation. `tools/website/sections.json` declares the published reading units; add future authorized translations there, then refresh website discovery links for new pages. The exporter does not translate new material or publish automatically.

## Content and provenance

The exporter reads the durable edition with accepted journal updates. It checks the selected English and German bodies, printed paragraph groups, note version/body fingerprints and local attachment text before producing HTML. A stale note fails the export rather than silently following a changed offset. Pandoc’s smart-punctuation conversion is disabled so it cannot alter stored punctuation.

Each section supplies HTML, downloadable Markdown and `records.json` with original version IDs, body hashes, note anchors and local terminology. `snapshot.json` identifies the source commit and fingerprints the generated files. Displayed note numbers are local to a complete reading page; semantic IDs remain stable. Do not hand-edit generated text. Correct the edition through its existing revision workflow and regenerate.

Latest drafts are included with explicit English-reading review labels. Website approval does not complete a pending translation review or certify German fidelity. The 1906 base, reported opening cancellation and unresolved readings remain qualified. No review markup, library PDF, generated SQLite store or raw worker stream is exported.

## Verification and publication

The checker compares HTML text with every exported body, preserves printed breaks, checks local links and search targets, and verifies one ordered note sequence per page. Python tests exercise stale attachments; Node tests exercise literal multilingual search and safe reading-position routes. Browser inspection remains a separate check: structural validation does not establish responsive rendering, focus behaviour or working interactive controls.

Before pushing, inspect each repository’s payload and run its publication/privacy gates. Verify the Pages build and compare live generated files with the local snapshot. Keep the website’s shared styles and unrelated pages unchanged, apart from the approved Resources and discovery links.

The [publication verification](website-verification.json) records the completed live-file comparison and distinguishes browser limits from passing content, link and search checks.
