# Humboldt translation project setup
<!-- SUMMARY: Authorized setup proposal and source-import record · status: implemented · updated: 2026-11-14 -->

The project folder is `/Users/brettreynolds/projects/LLM-CLI-projects/humboldt-grundzuege-translation`, as requested. The next bounded step is to make it a usable local repository with a documented German source and a clear starting point for translation.

## Source in hand

The Internet Archive holds a [University of Toronto scan of volume V](https://archive.org/details/gesammelteschrif05humbuoft) of Wilhelm von Humboldt’s *Gesammelte Schriften*. The title page identifies Albert Leitzmann as editor, Berlin, B. Behr’s Verlag, 1906. The opening of *Grundzüge des allgemeinen Sprachtypus* is visible on PDF page 374, corresponding to printed page 364.

The complete PDF, Archive OCR, and scan metadata have been downloaded into `sources/raw/`. Each matches the MD5 checksum reported by the Archive. The PDF has 496 pages; scan leaves and PDF page numbers differ, so references will record printed page, PDF page, and scan leaf separately.

## Proposed contents

| File or directory | Purpose |
| --- | --- |
| `README.md` | Project purpose, source identification, file guide, and current limits. |
| `AGENTS.md` | Brief project instructions, pointing to the parent workspace rules. |
| `docs/HANDOFF.md` | Verified current state and the next bounded translation step. |
| `sources/manifest.json` | Download URLs, checksums, edition metadata, and verification status. |
| `sources/page-map.json` | Map printed pages to the downloaded PDF and scan leaves. |
| `sources/grundzuege-ocr.txt` | Searchable extraction of the work, with page boundaries and an explicit uncorrected-OCR label. |
| `translations/` | Destination for subsequent English drafts. |

Initialize Git locally. Keep the downloaded originals available on disk and excluded from Git; retain their URLs and hashes in the manifest. Leave the repository uncommitted, with no remote configured.

## Proposed project instructions

Read `README.md` and `docs/HANDOFF.md` at the start of a session. Work in bounded passages. Check German against the scan before translating; preserve printed-page references and distinguish Humboldt’s text from the edition’s apparatus. Keep English drafts, translation notes, and unresolved readings separate. Label OCR and translation status accurately. Apply the inherited Roughdraft checkpoint to reviewable translation prose. Keep any comparison with Brett’s current theoretical framework in commentary rather than silently changing Humboldt’s wording.

## Completion and next step

Setup is complete when the source boundaries and page map have been checked, the files and local links validate, and Git reports the intended new files. This step prepares the source; no English translation is being proposed for approval here.

The next step will be a short bilingual pilot from the opening, after checking its complete German paragraph boundaries. Use it to settle recurring terminology before translating a longer passage.

## Authorization and outcome

Brett authorized both this setup and a short translation pilot on 2026-11-14 ("yes to both"). The proposal above is retained as the review record. Current files and verification limits are documented in [README.md](../README.md) and [HANDOFF.md](HANDOFF.md). The existing `AGENTS.md` remains unchanged as requested; its setup-era descriptions are historical. The [opening bilingual pilot](../translations/pilot-001.md) is a provisional draft for Roughdraft review. No commit, remote, or publication is authorized by this setup.
