"""Small, escaped HTML views for the local edition reader (no JavaScript)."""
from __future__ import annotations

from html import escape
import json
from urllib.parse import urlencode


def esc(value):
    return escape(str(value), quote=True)


def url(route, **values):
    return route + ('?' + urlencode(values) if values else '')


def link(label, route, **values):
    return '<a href="' + esc(url(route, **values)) + '">' + esc(label) + '</a>'


def inspect(label, value, opened=False):
    return '<details' + (' open' if opened else '') + '><summary>' + esc(label) + '</summary><pre>' + esc(json.dumps(value, ensure_ascii=False, indent=2)) + '</pre></details>'


def document(title, body):
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>''' + esc(title) + ''' — Humboldt reader</title><style>
body{font:18px/1.55 system-ui,sans-serif;max-width:1250px;margin:2rem auto;padding:0 1.3rem;color:#202830;background:#fbfaf6}a{color:#165d87}nav{display:flex;gap:1rem;flex-wrap:wrap;border-bottom:1px solid #bbb;padding-bottom:.8rem}h1{font-size:1.65rem}h2{font-size:1.3rem}h3{font-size:1.1rem}form{margin:1rem 0}input,select,textarea,button{font:inherit;max-width:100%;box-sizing:border-box;padding:.35rem}textarea{display:block;width:100%;min-height:9rem}label{display:block;margin:.6rem 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.82rem;background:#f0f1ef;padding:.8rem}summary{cursor:pointer}details{margin:.6rem 0}blockquote{margin:.6rem 0;border-left:3px solid #aab;padding:.6rem 1rem;white-space:pre-wrap}.muted{color:#52626b;font-size:.9rem}.tag{font-size:.8rem;background:#e8edf0;border-radius:3px;padding:.15rem .35rem}.notice{background:#fff0d8;padding:.8rem}.pair{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;border-top:1px solid #ccc;padding:.8rem 0}.words{white-space:pre-wrap}.word{text-decoration:none;border-bottom:1px dotted #8496a0}.word:hover{background:#deedf5}.card{padding:.6rem 0;border-bottom:1px solid #ccc}small{font-size:.8rem}@media(max-width:760px){.pair{grid-template-columns:1fr}}
</style><nav>''' + link('Read passages', '/') + '''<form action="/search" method="get" style="margin:0"><input name="q" aria-label="Search German or English" placeholder="Search German or English"><button>Search</button></form></nav><main><h1>''' + esc(title) + '</h1>' + body + '</main></html>'


def sources(items):
    if not items:
        return ''
    out = '<details><summary>Source attachments</summary><ul>'
    for item in items:
        path = item.get('path', '')
        label = item.get('label') or path or 'Unspecified source'
        out += '<li>' + (link(label, '/source', path=path) if item.get('available') else esc(label))
        if not item.get('available'):
            out += ' <span class="muted">' + esc(item.get('availability', 'Attachment unavailable; embedded text remains available.')) + '</span>'
        out += '</li>'
    return out + '</ul></details>'


def words(block):
    text = block['text']
    out, offset = [], 0
    for word in sorted(block.get('words', []), key=lambda w: (w['start'], w['end'], w['id'])):
        a, b = word['start'] - block['start'], word['end'] - block['start']
        if a < offset or b <= a or b > len(text):
            continue
        out += [esc(text[offset:a]), '<a class="word" href="' + esc(url('/trace', id=word['id'])) + '">' + esc(text[a:b]) + '</a>']
        offset = b
    out.append(esc(text[offset:]))
    return '<div class="words">' + ''.join(out) + '</div>'


def block_view(block):
    if block is None:
        return '<p class="muted">No recorded linked block.</p>'
    return '<div><small>' + (link(block.get('label') or block['kind'], '/trace', id=block['id']) if block.get('id') else esc(block['label'])) + '</small>' + words(block) + '</div>'


def _select(name, choices, selected, label):
    return '<label>' + esc(label) + ' <select name="' + esc(name) + '">' + ''.join('<option value="' + esc(key) + '"' + (' selected' if key == selected else '') + '>' + esc(title) + '</option>' for key, title in choices) + '</select></label>'


def home(section_choices, passage=None, de=None, en=None, attachments=()):
    body = '<p>Choose a section and versions, then click a word or block to inspect its source links, term senses, decisions and alternatives.</p>'
    if not section_choices:
        return document('Read passages', body + '<p class="notice">No section-labelled passages are recorded in this build. German and English search is still available.</p>')
    current = passage['section'] if passage else section_choices[0]['section']
    body += '<form method="get" action="/">' + _select('section', [(s['section'], s['label']) for s in section_choices], current, 'Section')
    if passage:
        versions = passage['versions']
        german = [v for v in versions if v['language'].casefold().startswith('de')]
        english = [v for v in versions if v['language'].casefold().startswith('en')]
        source = german or [v for v in versions if not v['language'].casefold().startswith('en')]
        defaults = passage.get('reading_defaults', {})
        source_choice = de if de is not None else defaults.get('source_id')
        target_choice = en if en is not None else defaults.get('target_id')
        left = next((v for v in source if v['id'] == source_choice), source[0] if source else None)
        right = None if en == '' else next((v for v in english if v['id'] == target_choice), english[0] if english else None)
        body += _select('de', [(v['id'], v['title'] + ' [' + v['id'] + ']') for v in source], left['id'] if left else '', 'German version' if german else 'Source version')
        body += _select('en', [('', 'No English version')] + [(v['id'], v['title'] + ' [' + v['id'] + ']') for v in english], right['id'] if right else '', 'English version')
    body += '<button>Show versions</button></form>'
    if not passage:
        return document('Read passages', body)
    body += '<p class="notice">' + esc(passage['note']) + ' Clickable words are recorded spans; their analyses may be provisional.</p>'
    for version in (left, right):
        if version:
            body += '<p><strong>' + link(version['title'], '/entity', kind='text_version', id=version['id']) + '</strong><br><span class="muted">' + esc(version['transcription_status']) + ' · ' + esc(version['locator']) + '</span></p>'
            body += inspect('Analysis methods and status', version['analyses'])
    linked = []
    if left and right:
        for alignment in passage['alignments']:
            if {alignment['left_version'], alignment['right_version']} == {left['id'], right['id']}:
                ls = [m['unit'] for m in alignment['members'] if m['unit'] and m['unit']['version_id'] == left['id']]
                rs = [m['unit'] for m in alignment['members'] if m['unit'] and m['unit']['version_id'] == right['id']]
                if ls and rs:
                    linked.append((alignment, ls, rs))
    linked.sort(key=lambda item: min(u['start'] for u in item[1]))
    block_l = {b['id'] for b in left['blocks']} if left else set()
    block_r = {b['id'] for b in right['blocks']} if right else set()
    main, spans = [], []
    for item in linked:
        (main if all(u['id'] in block_l for u in item[1]) and all(u['id'] in block_r for u in item[2]) else spans).append(item)
    used_l, used_r = set(), set()
    for alignment, ls, rs in main:
        def enriched(unit, version):
            return next((b for b in version['blocks'] if b['id'] == unit['id']), {**unit, 'words': []})
        body += '<div class="pair"><div>' + ''.join(block_view(enriched(u, left)) for u in sorted(ls,key=lambda u:u['start'])) + '</div><div>' + ''.join(block_view(enriched(u, right)) for u in sorted(rs,key=lambda u:u['start'])) + '</div></div>'
        body += inspect('Recorded alignment: ' + alignment['relation'] + ' (' + alignment['status'] + ')', {k:v for k,v in alignment.items() if k != 'members'})
        used_l.update(u['id'] for u in ls); used_r.update(u['id'] for u in rs)
    remaining_l = [b for b in left['blocks'] if b['id'] not in used_l] if left else []
    remaining_r = [b for b in right['blocks'] if b['id'] not in used_r] if right else []
    if remaining_l or remaining_r:
        body += '<p class="muted">The following blocks have no displayed recorded pairing. Column position does not assert an alignment.</p><div class="pair"><div>' + ''.join(block_view(b) for b in remaining_l) + '</div><div>' + ''.join(block_view(b) for b in remaining_r) + '</div></div>'
    if spans:
        body += '<h2>Additional span alignments</h2>'
        for alignment, ls, rs in spans:
            body += '<div class="pair"><div>' + ''.join(block_view({**u,'words':[]}) for u in sorted(ls,key=lambda u:u['start'])) + '</div><div>' + ''.join(block_view({**u,'words':[]}) for u in sorted(rs,key=lambda u:u['start'])) + '</div></div>'
            body += inspect('Recorded alignment: ' + alignment['relation'] + ' (' + alignment['status'] + ')', {k:v for k,v in alignment.items() if k != 'members'})
    return document(passage['label'], body + sources(attachments))


def search_view(query, results):
    body = '<p>' + esc(len(results)) + ' results. Exact headwords and ranked English renderings precede incidental prose matches.</p>'
    for r in results:
        target = link(r['label'], '/trace', id=r['unit_id']) if r.get('unit_id') else link(r['label'], '/entity', kind=r['kind'], id=r['id'])
        body += '<article class="card"><h2>' + target + '</h2><span class="tag">' + esc(r['match_field']) + '</span> <span class="muted">' + esc(r['language']) + '</span><blockquote>' + esc(r['snippet']) + '</blockquote></article>'
    return document('Search: ' + query, body or '<p>No matches.</p>')


def _decision(decision):
    return '<article class="card"><h3>' + link(decision['question'], '/entity', kind='decision', id=decision['id']) + '</h3><p>' + esc(decision['resolution']) + '</p><p class="muted">' + esc(decision['authority']) + ' · ' + esc(decision['status']) + '</p>' + inspect('How this decision is linked', decision.get('links', [])) + '</article>'


def _evidence(record):
    return '<article class="card"><h3>' + link(record['locator'], '/entity', kind='evidence', id=record['id']) + '</h3><blockquote>' + esc(record['excerpt']) + '</blockquote><p>' + esc(record['statement']) + '</p><p class="muted">Quotation: ' + esc(record['quote_status']) + ' · Claim: ' + esc(record['claim_status']) + '</p>' + inspect('Evidence metadata and link scope', record) + '</article>'


def trace_view(data, attachments=()):
    unit = data['unit']
    body = '<blockquote>' + esc(unit['text']) + '</blockquote><p class="muted">' + esc(unit['version_title']) + ' · ' + esc(unit['kind']) + ' · ' + esc(unit['id']) + '</p><p class="notice">' + esc(data['note']) + '</p>'
    body += '<h2>Term associations</h2>'
    for term in data['terms']:
        if term['lexeme'] and term['sense']:
            body += '<p><span class="tag">' + esc(term['scope']) + '</span> ' + link(term['lexeme']['headword'] + ' — ' + term['sense']['label'], '/entity', kind='term_sense', id=term['sense']['id']) + '<br>' + esc(term['sense']['definition']) + '</p>'
    for discovery in data['term_discoveries']:
        obj = next((o for o in data['term_objects'] if o['record']['id'] == discovery['lexeme_id']), None)
        if obj:
            body += '<p><span class="tag">context / form discovery</span> ' + link(obj['record']['headword'], '/entity', kind='lexeme', id=discovery['lexeme_id']) + ' — no local sense assigned.</p>'
    body += '<h2>Decisions and rationale</h2>' + (''.join(_decision(d) for d in data['decisions']) or '<p>No linked decision is recorded.</p>')
    body += '<h2>Evidence</h2>' + (''.join(_evidence(e) for e in data['evidence']) or '<p>No linked evidence is recorded.</p>')
    body += '<h2>Alternative versions</h2>' + ''.join('<p>' + link(v['title'], '/entity', kind='text_version', id=v['id']) + ' <span class="muted">' + esc(v['transcription_status']) + '</span></p>' for v in data['alternatives'])
    for title,key in [('Ancestry','ancestors'),('Overlapping and containing annotations','annotations'),('All contextual links','context_links'),('Analysis status','analyses'),('Recorded alignments','alignments'),('Revision history and impacts','history')]:
        body += inspect(title, data.get(key, []))
    return document('Trace: ' + (unit['label'] or unit['kind']), body + sources(attachments))


def entity_view(data, attachments=()):
    from .records import record_id
    from .revisions import SUPPORTED
    row, kind = data['record'], data['kind']
    identifier=record_id(kind,row)
    title = row.get('headword') or row.get('title') or row.get('label') or row.get('question') or identifier
    body = '<p class="muted">' + esc(kind) + ' · ' + esc(identifier) + '</p>'
    if kind == 'lexeme':
        for sense in data['senses']:
            body += '<article class="card"><h2>' + link(sense['label'], '/entity', kind='term_sense', id=sense['id']) + '</h2><p>' + esc(sense['definition']) + '</p><p><strong>English:</strong> ' + esc(' / '.join(r['rendering'] for r in sense['renderings'])) + '</p><p><strong>Rule:</strong> ' + esc(sense['rule']) + '</p><p><strong>Caution:</strong> ' + esc(sense['caution']) + '</p>' + inspect('Attestations, uses and composite expressions', sense) + '</article>'
    elif kind == 'term_sense':
        sense = data['sense']
        body += '<p><strong>English:</strong> ' + esc(' / '.join(r['rendering'] for r in sense['renderings'])) + '</p>'
        for field in ('definition','rule','caution'):
            body += '<h2>' + esc(field.capitalize()) + '</h2><p>' + esc(row[field]) + '</p><p>' + link('Draft a revision to ' + field, '/propose', kind=kind, id=row['id'], field=field) + '</p>'
    elif kind == 'decision':
        body += '<p>' + esc(row['resolution']) + '</p><p class="muted">' + esc(row['authority']) + ' · ' + esc(row['status']) + '</p><p>' + link('Draft a revised resolution', '/propose', kind=kind, id=row['id'], field='resolution') + '</p>'
    elif kind == 'text_version':
        body += '<p class="notice">' + esc(row['transcription_status']) + '</p>' + ''.join(block_view(b) for b in data['blocks']) + '<p>' + link('Draft a new text version', '/propose', kind=kind, id=row['id'], field='body') + '</p>'
        if data.get('predecessor_id'):body+='<p>'+link('Previous text version','/entity',kind=kind,id=data['predecessor_id'])+'</p>'
        for successor in data.get('successors',[]):body+='<p>Superseded by '+link(successor['title']+' ['+successor['id']+']','/entity',kind=kind,id=successor['id'])+'</p>'
    elif kind == 'evidence':
        body += _evidence(data['evidence'])
    if kind=='lexeme':
        body+='<h2>Recorded forms</h2>'+''.join('<p>'+link(r['form'],'/entity',kind='lexeme_form',id=record_id('lexeme_form',r))+'</p>' for r in data.get('forms',[]))
    if kind=='term_sense':
        body+='<h2>English rendering records</h2>'+''.join('<p>'+link(r['rendering'],'/entity',kind='sense_rendering',id=record_id('sense_rendering',r))+'</p>' for r in data['sense']['renderings'])
    if kind=='alignment':
        body+='<h2>Correspondence members</h2>'+''.join('<p>'+link(r['side']+': '+r['unit_id'],'/entity',kind='alignment_member',id=record_id('alignment_member',r))+'</p>' for r in data.get('members',[]))
    handled={'term_sense':{'definition','rule','caution'},'decision':{'resolution'},'text_version':{'body'}}.get(kind,set())
    fields=sorted(SUPPORTED.get(kind,set())-handled)
    if fields:body+='<h2>Propose a record amendment</h2>'+''.join('<p>'+link('Revise '+field,'/propose',kind=kind,id=identifier,field=field)+'</p>' for field in fields)
    body += inspect('Full record, rationale, links and history', data, opened=kind not in ('lexeme','term_sense','decision','text_version','evidence'))
    return document(title, body + sources(attachments))


def proposal_view(kind, row, field, fingerprint):
    from .records import record_id
    body = '<p class="notice">This form downloads a proposal draft. It does not save, apply or accept a change. Import the downloaded JSON using the project CLI, then record an explicit decision there. Text edits propose a new version; existing readings survive.</p><form method="post" action="/proposal">'
    for name,value in [('kind',kind),('target_id',record_id(kind,row)),('field',field),('target_sha256',fingerprint)]:
        body += '<input type="hidden" name="' + name + '" value="' + esc(value) + '">'
    required='' if field in {'caution','note','locator','provenance'} else ' required'
    body += '<label>Proposed ' + esc(field) + '<textarea name="value"'+required+'>' + esc(row[field]) + '</textarea></label><label>Your name <input name="by" required maxlength="200"></label><label>Reason <textarea name="reason" required></textarea></label><label>Existing evidence IDs (JSON array); import new evidence as a dataset first, or describe a new citation in Reason<textarea name="evidence">[]</textarea></label><button>Download proposal draft JSON</button></form>'
    return document('Draft a revision', body)
