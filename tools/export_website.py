#!/usr/bin/env python3
"""Export the developing edition to a static website; never rewrite its sources.

Uses the existing Pandoc executable at export time. Hosting needs no runtime
dependencies. Add future authorized divisions to tools/website/sections.json.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from functools import lru_cache
import hashlib
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(__file__).parent / 'website'
sys.path.insert(0, str(ROOT / 'src'))
BASE = 'https://brettreynolds.ca/humboldt/'
REPO = 'https://github.com/BrettRey/humboldt-grundzuege-translation'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(sid):
    match = re.match(r'^p(\d+[a-z]?):', sid)
    return match[1] if match else None


def check_anchor(note, version, unit):
    if note['target_version'] != version['id'] or unit['version_id'] != version['id'] or note['target_body_sha256'] != version['body_sha256']:
        raise ValueError('Note requires semantic reattachment: ' + note['id'])
    text = version['body'][unit['start']:unit['end']]
    offset = note['anchor']['offset_in_rendering']
    fragment = note['anchor']['after']
    if not 0 <= offset <= len(text):
        raise ValueError('Note offset outside rendering: ' + note['id'])
    if fragment not in {'complete source rendering block', 'complete rendering block'} and not text[:offset].endswith(fragment):
        raise ValueError('Note anchor differs: ' + note['id'])
    return unit['start'] + offset


@lru_cache(maxsize=None)
def markdown(text):
    result = subprocess.run(['pandoc', '--from=markdown-smart', '--to=html5', '--wrap=none'], input=text,
                            text=True, capture_output=True, check=True).stdout.strip()
    # Repository-relative scholarly links resolve to the exact public source tree.
    def link(match):
        href = match[1]
        if href.startswith('#') or urlsplit(href).scheme:
            return match[0]
        # Notes were authored from translations/<section>/; ../../ targets root.
        if href.startswith('../../'):
            href = href[6:]
        return 'href="' + escape(REPO + '/blob/' + SOURCE_COMMIT + '/' + href, quote=True) + '"'
    return re.sub(r'href="([^"]+)"', link, result)


def inline(text):
    value = markdown(text)
    return value[3:-4] if value.startswith('<p>') and value.endswith('</p>') else value


def note_ref(note):
    nid = escape(note['id'], quote=True)
    return (f'<sup><a class="note-ref" id="ref-{nid}" href="#note-{nid}" '
            f'aria-label="Note {note["display_number"]}, {escape(note["attribution"])}">'
            f'{note["display_number"]}</a></sup>')


def model():
    from humboldt.ingest import load
    tables, _ = load(ROOT)
    versions = {v['id']: v for v in tables['text_version']}
    units = {u['id']: u for u in tables['unit']}
    evidence = {e['id']: e for e in tables['evidence']}
    defaults = {d['section']: d for d in read(ROOT / 'edition/manifest.json')['reading_defaults']}
    sections = []
    for spec in read(ASSETS / 'sections.json'):
        folder = ROOT / 'translations' / spec['folder']
        final, source = read(folder / 'revised.json'), read(folder / 'source.json')
        annotation = read(ROOT / 'translations' / spec['annotations'] / 'notes.json')
        if spec.get('sample'):
            paragraphs = [dict(number=147, sentences=[dict(source_id='p147:' + s['id'], english=s['text']) for s in final['sentences']], typographic_groups=[list(range(1, len(final['sentences']) + 1))])]
        else:
            paragraphs = final['paragraphs']
        wanted = {str(p['number']) for p in paragraphs}
        selected = [n.copy() for n in annotation['notes'] if number(n['source_id']) in wanted]
        for n in selected:
            n['text'] = evidence[spec['prefix'] + 'note:' + n['id']]['excerpt']
        # Keep printed reading order; numbering is local to this complete page.
        for i, n in enumerate(selected, 1):
            n['display_number'] = i
        guides = [g.copy() for g in annotation['term_guide'] if spec['annotations'] != 'annotated' or any(number(s) in wanted for s in g['source_ids'])]
        for g in guides:
            g['text'] = evidence[spec['prefix'] + 'guide:' + g['id']]['excerpt']
        review = ROOT / 'translations' / spec['review'] / 'review.json'
        reviewed = review.exists() and read(review).get('completed', False)
        result = dict(spec, reviewed=reviewed, status='English-reading review completed' if reviewed else 'English-reading review pending', notes=selected, guides=guides, paragraphs=[], source=source, headings=[])
        for p in paragraphs:
            label = str(p['number'])
            default = defaults[label]
            en, de = versions[default['target_id']], versions[default['source_id']]
            texts = [s['english'] for s in p['sentences']]
            if ' '.join(texts) != en['body']:
                raise ValueError('Reading differs from current recorded English: ' + label)
            groups = p['typographic_groups']
            if [i for group in groups for i in group] != list(range(1, len(texts) + 1)):
                raise ValueError('Incomplete printed paragraph groups: ' + label)
            offsets = {s['source_id']: sum(len(t) + 1 for t in texts[:i]) for i, s in enumerate(p['sentences'])}
            insertions = defaultdict(list)
            for n in selected:
                if number(n['source_id']) != label:
                    continue
                if n['source_version'] != de['id'] or units[n['source_unit']]['version_id'] != de['id']:
                    raise ValueError('Note/source version differs: ' + n['id'])
                if n.get('source_body_sha256', de['body_sha256']) != de['body_sha256']:
                    raise ValueError('Note/source body differs: ' + n['id'])
                position = check_anchor(n, en, units[n['target_unit']])
                n['_absolute_offset'] = position
                if n.get('display_at') == 'work_title':
                    continue
                expected = offsets[n['source_id']] + n['anchor']['offset_in_rendering']
                if position != expected:
                    raise ValueError('Note/source rendering mismatch: ' + n['id'])
                insertions[position].append(n)
            grouped = []
            for group in groups:
                start = sum(len(t) + 1 for t in texts[:group[0] - 1])
                text = ' '.join(texts[i - 1] for i in group)
                for position in sorted(insertions, reverse=True):
                    if start <= position <= start + len(text):
                        relative = position - start
                        text = text[:relative] + ''.join(note_ref(n) for n in insertions[position]) + text[relative:]
                grouped.append(markdown(text))
            source_p = source if spec.get('sample') else next(x for x in source['paragraphs'] if str(x['number']) == label)
            de_texts = [s['text'] for s in source_p['sentences']]
            if ' '.join(de_texts) != de['body']:
                raise ValueError('Checked German differs from source version: ' + label)
            de_groups = source_p.get('typographic_groups', [list(range(1, len(de_texts) + 1))])
            # German and English segmentation can differ; use the source's declared groups.
            if [i for g in de_groups for i in g] != list(range(1, len(de_texts) + 1)):
                raise ValueError('Incomplete German paragraph groups: ' + label)
            german = [' '.join(de_texts[i - 1] for i in g) for g in de_groups]
            result['paragraphs'].append(dict(number=label, english=en['body'], german=de['body'], html='\n'.join(grouped), english_groups=[' '.join(texts[i - 1] for i in g) for g in groups], german_groups=german, source_id=de['id'], target_id=en['id'], source_sha256=de['body_sha256'], target_sha256=en['body_sha256'], locator=de['locator']))
        ancillary = {x['source_id']: x['english'] for x in final.get('ancillary', [])}
        for h in source.get('headings', []):
            result['headings'].append(dict(before=str(h['before']), text=ancillary[h['id']], id=h['id']))
        if final.get('heading_English'):
            result['headings'].append(dict(before=str(paragraphs[0]['number']), text=final['heading_English'], id='heading:part-i'))
        sections.append(result)
    return sections


def navigation(sections, current=None):
    links = []
    for s in sections:
        selected = 'aria-current="page"' if s['slug'] == current else ''
        links.append(f'<li><a {selected} href="/humboldt/{s["slug"]}/">{escape(s["title"])} <span class="meta">{escape(s["range"])}</span></a></li>')
    return '<nav aria-label="Translation contents"><ol class="contents">' + ''.join(links) + '</ol></nav>'


def search_form():
    return '''<form class="search" role="search"><label for="search-input">Search this developing edition</label>
<div class="search-row"><input id="search-input" name="q" type="search" placeholder="English, German, a term or passage number" autocomplete="off"><button type="submit">Search</button></div><noscript><p class="meta">Search needs JavaScript. All reading pages, German text and notes remain available; use your browser’s Find command within a page.</p></noscript>
<p id="search-status" class="meta" role="status"></p><ol id="search-results"></ol></form>'''


def shell(title, content, slug='', description='A developing English translation of Humboldt’s Grundzüge des allgemeinen Sprachtypus, with German text and attributed notes.'):
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} · Humboldt · Brett Reynolds</title><meta name="description" content="{escape(description, quote=True)}">
<link rel="canonical" href="{BASE + slug}"><script src="/theme.js"></script><link rel="stylesheet" href="/style-v3.css">
<link rel="stylesheet" href="/humboldt/reader.css"><script type="module" src="/humboldt/reader.js"></script></head>
<body class="humboldt" data-section-slugs="{SECTION_SLUGS}"><a class="skip" href="#main">Skip to reading</a>
<header class="site-header"><a href="/">Brett Reynolds</a><span aria-hidden="true"> / </span><a href="/humboldt/">Humboldt</a></header>
{content}
<footer class="edition-footer"><p>AI-assisted research translation in development. English-reading review does not certify German fidelity.</p>
<p>Translation and original commentary: <a href="/humboldt/content-license.txt">CC BY 4.0</a>. Reader software: <a href="/humboldt/code-license.txt">MIT</a>. Historical source and third-party material retain their own status; see the <a href="{REPO}/blob/{SOURCE_COMMIT}/NOTICE.md">attribution notice</a>.</p>
<p><a href="/humboldt/#about">About the edition</a> · <a href="{REPO}/tree/{SOURCE_COMMIT}">Source and editorial record</a> · <a href="/humboldt/snapshot.json">Edition snapshot</a></p></footer>
<dialog id="note-dialog" aria-labelledby="note-heading"><div class="dialog-head"><h2 id="note-heading">Note</h2><button type="button" id="close-note">Close</button></div><div id="note-body"></div><a id="note-original">Go to the endnote</a></dialog>
<p id="action-status" class="sr-only" role="status"></p></body></html>'''


def section_page(section, sections):
    slug = section['slug']
    title_notes = ''.join(note_ref(n) for n in section['notes'] if n.get('display_at') == 'work_title')
    status = escape(section['status'])
    intro = f'''<div class="reading-top"><p class="eyebrow">Wilhelm von Humboldt · developing translation</p>
<p class="work-name"><cite>Outlines of the General Type of Language</cite>{title_notes}</p><h1>{escape(section['title'])}</h1>
<p class="meta">Passages {escape(section['range'])} · {status}</p><p>{escape(section['description'])}</p></div>
<details class="section-menu"><summary>Contents and search</summary>{navigation(sections, slug)}<nav class="passage-index" aria-label="Passages in this section"><span class="meta">Jump to passage</span><div>{' '.join('<a href="#p' + p['number'] + '">' + p['number'] + '</a>' for p in section['paragraphs'])}</div></nav>{search_form()}</details>
<div class="reader-controls"><button type="button" id="parallel-toggle" aria-pressed="false" hidden>Show parallel German</button><a href="#terminology">Terminology</a><a href="#notes">Notes</a><a href="reading.md" download>Markdown</a><button type="button" id="print-reading" hidden>Print</button></div>'''
    if slug == 'introduction':
        intro += '<aside class="source-notice"><p>Drechsel (2024:155) reports cancellation of the first seven passages. The manuscript marks, their extent and editorial meaning have not been independently verified. This translation follows the 1906 print; the report is not extended to later passages.</p></aside>'
    intro += '<p class="reading-help meta">Open a note number to read it nearby. Each passage also has its German text, source-page link and permanent reference. Historical judgments about peoples and languages remain Humboldt’s.</p>'
    parts = ['<main id="main">', intro, '<div id="reading">']
    for p in section['paragraphs']:
        n = p['number']
        for h in section['headings']:
            if h['before'] == n:
                parts.append(f'<h2 class="printed-heading" id="{escape(h["id"], quote=True)}">{escape(h["text"])}</h2>')
        citation = f'Wilhelm von Humboldt, Outlines of the General Type of Language, passage {n}. Developing English translation, edition {SOURCE_COMMIT[:7]}. {BASE}{slug}/#p{n}'
        # Scanleaf coordinates are retained separately in snapshot metadata.
        match = re.search(r'PDF\s*(\d+)', p['locator'], re.I)
        if section.get('sample'):
            match = re.search(r'PDF\s*(\d+)', p['locator'], re.I)
        pdf_page = int(match[1]) if match else None
        if pdf_page is None:
            coords = section['source'].get('coordinates', {})
            pdf_page = coords.get('pdf_page')
        if pdf_page is None:
            raise ValueError('Missing PDF locator: ' + n + ' ' + p['locator'])
        scan = 'https://archive.org/download/gesammelteschrif05humbuoft/gesammelteschrif05humbuoft.pdf#page=' + str(pdf_page)
        record = f'{REPO}/blob/{SOURCE_COMMIT}/translations/{section["folder"]}/source.json'
        feedback = REPO + '/issues/new?' + 'title=' + quote('Translation comment: passage ' + n) + '&body=' + quote(citation + '\n\nSuggested correction or question:\n')
        parts.append(f'''<article class="passage" id="p{n}" aria-labelledby="label-{n}">
<header class="passage-tools"><h3 id="label-{n}"><a href="#p{n}" aria-label="Permanent link to passage {n}">{n}</a></h3><div><button type="button" class="copy-citation" data-citation="{escape(citation, quote=True)}" hidden>Copy citation</button><a href="{record}">Record</a><a href="{escape(feedback, quote=True)}">Suggest a correction</a></div></header>
<div class="language-pair"><div class="english" lang="en">{p['html']}</div>
<details class="german" lang="de"><summary><span lang="en">German · {escape(p['locator'])}</span></summary>{''.join('<p>' + escape(t) + '</p>' for t in p['german_groups'])}<p class="source-links" lang="en"><a href="{scan}">Open scanned page</a> · <a href="{record}">Checked transcription</a></p></details></div></article>''')
    parts += ['</div>', '<section id="terminology"><h2>Terminology guide</h2><p class="meta">Local reading aids for this section. They do not impose fixed English equivalents across the whole work.</p>']
    for g in section['guides']:
        parts.append(f'<article class="term-entry" id="term-{escape(g["id"], quote=True)}"><h3>{escape(g["term"])}</h3><p class="german-terms" lang="de">{escape(", ".join(g["German"]))}</p>{markdown(g["text"])}</article>')
    parts += ['</section>', '<section id="notes"><h2>Notes</h2><p class="meta">Humboldt: his own notes. 1906 Ed.: the print editor’s apparatus. Trans.: our explanations and qualifications. One Arabic sequence covers all three.</p><ol class="endnotes">']
    for n in section['notes']:
        parts.append(f'<li id="note-{escape(n["id"], quote=True)}" data-number="{n["display_number"]}" tabindex="-1"><div class="note-text">{markdown(n["text"] + " (" + n["attribution"] + ")")}</div><a class="note-back" href="#ref-{escape(n["id"], quote=True)}" aria-label="Return to note {n["display_number"]} in the reading">Return to text ↑</a></li>')
    parts += ['</ol></section>']
    current = next(i for i, s in enumerate(sections) if s['slug'] == slug)
    contiguous = [s for s in sections if not s.get('sample')]
    previous = sections[current - 1] if current and not section.get('sample') else None
    following = contiguous[current + 1] if current + 1 < len(contiguous) else None
    parts.append('<nav class="next-previous" aria-label="Reading sequence">')
    if previous:
        parts.append(f'<a rel="prev" href="../{previous["slug"]}/">← {escape(previous["title"])}</a>')
    if following:
        parts.append(f'<a rel="next" href="../{following["slug"]}/">{escape(following["title"])} →</a>')
    elif not section.get('sample'):
        parts.append('<span class="meta">Next: Vocabulary, 72–126 · not yet translated</span>')
    else:
        parts.append('<a href="../">← Back to contents</a>')
    parts.append('</nav></main>')
    return shell(section['title'], '\n'.join(parts), slug + '/')


def home_page(sections):
    rows = ''.join(f'<li><a href="{s["slug"]}/"><span class="contents-title">{escape(s["title"])}</span><span class="meta">{escape(s["range"])}</span></a><p>{escape(s["description"])}</p><p class="review-status">{escape(s["status"])}</p></li>' for s in sections if not s.get('sample'))
    sample = next(s for s in sections if s.get('sample'))
    text = f'''<main id="main"><div class="reading-top"><p class="eyebrow">Wilhelm von Humboldt</p><h1>Outlines of the General Type of Language</h1>
<p class="original-title" lang="de"><cite>Grundzüge des allgemeinen Sprachtypus</cite></p><p class="edition-deck">A developing English translation</p>
<p>Read Humboldt’s account of language, with the German available alongside the English, explanatory notes and a record of consequential translation choices.</p>
<p class="meta">Available in sequence: passages 1–71, including 62a and 62b. Vocabulary and the remaining division are still to come.</p><a class="start-reading" href="introduction/">Begin with the Introduction →</a><a class="resume-reading" hidden>Resume reading →</a></div>
<section class="edition-contents"><h2>Read the translation</h2><ol>{rows}<li class="not-yet"><span class="contents-title">Vocabulary</span><span class="meta">72–126 · not yet translated</span></li><li class="not-yet"><span class="contents-title">Combination into discourse</span><span class="meta">127–149 · not yet translated as a complete division</span></li></ol><p class="sample-link">A separate later sample is also available: <a href="{sample['slug']}/">passage 147, on grammatical form</a>. It is not the continuation of passage 71.</p></section>
<section><h2>Find a passage or term</h2>{search_form()}</section>
<section id="about"><h2>About this developing edition</h2>
<p>The base text is Albert Leitzmann’s 1906 edition, <cite>Gesammelte Schriften</cite>, volume V, pages 364–473. This is a provisional research translation, not a critical edition. The 2017 critical edition has not been acquired, and the manuscript has not been collated.</p>
<p>The translation uses independent model candidates, source-based synthesis, fresh model audits and an explicit record of the resulting decisions. English-reading review concerns clarity and editorial usefulness; it is not specialist certification of German fidelity. Each section shows its own review status.</p>
<p>The first seven passages carry a reported cancellation that has not been independently manuscript-verified; the Introduction explains it. Historical assertions and evaluations remain in the translation, with focused qualifications in the notes. Unresolved readings remain visible.</p>
<p>Note labels identify the author: <strong>(Humboldt)</strong>, <strong>(1906 Ed.)</strong> and <strong>(Trans.)</strong>. The German preserves historical spelling. The English follows Oxford spelling and uses local terminology guides to explain consequential distinctions.</p>
<p>This website is generated from the edition records. Permanent paragraph links and snapshot-specific citations make the current draft identifiable as it develops. Source versions, alternative translations, audit findings and correction history remain in the <a href="{REPO}">public repository</a>.</p>
<p>Your reading position and choice of English or parallel text are remembered on this device.</p>
<p>Suggestions are welcome through the correction link on each passage, or by <a href="mailto:brett.reynolds@humber.ca?subject=Humboldt%20translation">email</a>. Please include the passage number and, where relevant, the German wording.</p></section></main>'''
    return shell('Developing translation', text)


def download(section):
    lines = ['# ' + section['title'], '', 'Wilhelm von Humboldt · developing English translation', '', section['status'] + '; German fidelity remains provisional.', '', 'Edition snapshot: ' + SOURCE_COMMIT, '', 'Source: GS V, Leitzmann 1906. ' + REPO, '']
    title_notes = [n for n in section['notes'] if n.get('display_at') == 'work_title']
    if title_notes:
        lines += ['Outlines of the General Type of Language' + ''.join('[^' + n['id'] + ']' for n in title_notes), '']
    # Build Markdown from exact bodies, inserting note markers at checked unit offsets.
    for p in section['paragraphs']:
        for h in section['headings']:
            if h['before'] == p['number']:
                lines += ['## ' + h['text'], '']
        positions = defaultdict(list)
        for n in section['notes']:
            if number(n['source_id']) == p['number'] and n.get('display_at') != 'work_title':
                positions[n['_absolute_offset']].append(n)
        start = 0
        for i, group in enumerate(p['english_groups']):
            text = group
            for at in sorted(positions, reverse=True):
                if start <= at <= start + len(group):
                    relative = at - start
                    text = text[:relative] + ''.join('[^' + n['id'] + ']' for n in positions[at]) + text[relative:]
            lines += [('**' + p['number'] + '** ' if i == 0 else '') + text, '']
            start += len(group) + 1
    lines += ['## Terminology guide', '']
    for g in section['guides']:
        lines += ['**' + g['term'] + '** (' + ', '.join(g['German']) + '). ' + g['text'], '']
    lines += ['## Notes', '']
    for n in section['notes']:
        lines += ['[^' + n['id'] + ']: ' + n['text'] + ' (' + n['attribution'] + ')', '']
    return '\n'.join(lines)


def export(output):
    global SOURCE_COMMIT, SECTION_SLUGS
    SOURCE_COMMIT = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if not shutil.which('pandoc'):
        raise ValueError('Export requires the existing Pandoc executable; hosting has no runtime dependencies.')
    sections = model()
    SECTION_SLUGS = ' '.join(s['slug'] for s in sections)
    output.mkdir(parents=True, exist_ok=True)
    search = []
    snapshot = dict(format='humboldt.website-snapshot', version=1, source_commit=SOURCE_COMMIT, source_repository=REPO, manifest_sha256=sha(ROOT / 'edition/manifest.json'), sections=[], files=[])
    for section in sections:
        folder = output / section['slug']; folder.mkdir(exist_ok=True)
        (folder / 'index.html').write_text(section_page(section, sections))
        (folder / 'reading.md').write_text(download(section))
        provenance = dict(slug=section['slug'], title=section['title'], range=section['range'], review_status=section['status'], headings=section['headings'], paragraphs=[{k:v for k,v in p.items() if k not in {'html'}} for p in section['paragraphs']], notes=[{k:v for k,v in n.items() if not k.startswith('_')} for n in section['notes']], terminology=section['guides'])
        (folder / 'records.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n')
        snapshot['sections'].append(dict(slug=section['slug'], title=section['title'], passages=[p['number'] for p in section['paragraphs']], review_status=section['status'], note_count=len(section['notes'])))
        for p in section['paragraphs']:
            search.append(dict(title=section['title'] + ' · ' + p['number'], href='/humboldt/' + section['slug'] + '/#p' + p['number'], kind='Passage', text='p' + p['number'] + ' ' + p['english'] + '\n' + p['german']))
        for n in section['notes']:
            search.append(dict(title=section['title'] + ' · note ' + str(n['display_number']), href='/humboldt/' + section['slug'] + '/#note-' + n['id'], kind=n['attribution'], text=n['text']))
        for g in section['guides']:
            search.append(dict(title=g['term'] + ' · ' + section['title'], href='/humboldt/' + section['slug'] + '/#term-' + g['id'], kind='Terminology', text=', '.join(g['German']) + ' ' + g['text']))
    (output / 'index.html').write_text(home_page(sections))
    (output / 'search-index.json').write_text(json.dumps(search, ensure_ascii=False, separators=(',', ':')) + '\n')
    for asset in ['reader.css', 'reader.js']:
        shutil.copyfile(ASSETS / asset, output / asset)
    for source, target in [('LICENSE', 'code-license.txt'), ('LICENSE-CONTENT', 'content-license.txt')]:
        (output / target).write_text((ROOT / source).read_text().rstrip('\n') + '\n')
    for path in sorted(output.rglob('*')):
        if path.is_file() and path.name != 'snapshot.json':
            snapshot['files'].append(dict(path=path.relative_to(output).as_posix(), sha256=sha(path)))
    (output / 'snapshot.json').write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(output=str(output), sections=len(sections), passages=sum(len(s['paragraphs']) for s in sections), notes=sum(len(s['notes']) for s in sections), files=len(snapshot['files']) + 1)))
    return snapshot


SOURCE_COMMIT = ''
SECTION_SLUGS = ''
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Dedicated humboldt/ directory in the website checkout or a temporary export')
    args = parser.parse_args()
    export(args.output.resolve())
