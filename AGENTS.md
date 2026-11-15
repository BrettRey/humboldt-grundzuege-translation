# Repository Guidelines

## Project Structure & Source Materials

This project prepares an English translation of Humboldt’s *Grundzüge des allgemeinen Sprachtypus*.

- `sources/raw/gs-v-1906.pdf`: scanned volume V of the German edition.
- `sources/raw/gs-v-1906-ocr.txt`: searchable OCR, requiring comparison with the scan.
- `sources/raw/scandata.xml`: scan metadata.
- `docs/SETUP-REVIEW.md`: proposed repository layout and source-preparation workflow, awaiting review.

Preserve downloaded originals. Keep corrected transcriptions, English drafts, translation notes, and unresolved readings separate. The additional paths described in the setup review are proposed, not established directories. There are currently no application modules or test directories.

## Build, Test, and Development Commands

No build system, dependency installation, development server, or automated test suite is configured. Useful commands from the project root are:

- `open sources/raw/gs-v-1906.pdf`: inspect the scan on macOS.
- `rg -n 'Sprachtypus' sources/raw/gs-v-1906-ocr.txt`: locate candidate passages in the OCR.
- `shasum -a 256 sources/raw/*`: calculate source fingerprints; compare against recorded hashes when available.

OCR search results locate text; verify readings against the page image.

## Style & Naming Conventions

Write UTF-8 Markdown with descriptive headings, short paragraphs, and hyphen bullets. Indent nested lists by two spaces. Use lowercase, hyphen-separated names for new prose files, such as `terminology-notes.md`. No formatter or linter is configured.

Preserve German spelling and punctuation in transcriptions. Label uncorrected OCR, draft translations, and checked passages explicitly. Keep commentary on modern theoretical frameworks separate from Humboldt’s wording.

## Validation Guidelines

Validate each changed passage manually against the scan. Check complete paragraph boundaries, omissions, terminology, and the distinction between Humboldt’s text and editorial apparatus. Record printed page, PDF page, and scan leaf separately. Check local links and any added metadata. Automated coverage requirements and test naming conventions do not yet apply.

## Commit & Pull Request Guidelines

This directory has no Git repository or commit history yet. After initialization, use concise imperative subjects, for example `Document source provenance`. Keep changes limited to one passage or setup task. Pull requests should identify affected passages, checks performed, unresolved readings, and any related issue. Include page images only when needed to explain a reading.

## Agent Instructions

Follow `../AGENTS.md` and `../CLAUDE.md`. Stay within the requested passage or setup task. Use Roughdraft checkpoints for reviewable translation prose and substantial workflow changes, following the parent guidance.
