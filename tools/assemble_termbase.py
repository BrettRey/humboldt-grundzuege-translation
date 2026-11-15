#!/usr/bin/env python3
"""Assemble source-grounded term records; fail on unaccounted candidates/evidence."""
import argparse
from collections import Counter, defaultdict
import hashlib
from functools import lru_cache
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'sources/terminology/v2'
RANGES = {'early': (364, 399), 'middle': (400, 444), 'late': (445, 473)}
DISPOSITIONS = {'included', 'ordinary', 'cited_example', 'proper_name', 'apparatus_only', 'ocr_noise', 'needs_review'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


@lru_cache(maxsize=None)
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(text):
    return unicodedata.normalize('NFC', re.sub(r'\s+', ' ', text).strip()).casefold()


def slug(text):
    text = text.translate(str.maketrans({'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'Ä': 'ae', 'Ö': 'oe', 'Ü': 'ue', 'ß': 'ss'}))
    text = ''.join(c for c in unicodedata.normalize('NFKD', text).casefold() if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')


def span(text, quote):
    """Require a contiguous unique source span; never approximate a quotation."""
    starts = [m.start() for m in re.finditer(re.escape(quote), text)]
    if len(starts) != 1:
        raise ValueError(f'expected one exact quotation anchor, got {len(starts)}: {quote[:90]!r}')
    return starts[0], starts[0] + len(quote)


def assemble(strict=True):
    pages = {p['printed_page']: p for p in read(ROOT/'sources/terminology/search-pages.json')}
    ocr_stream='\n\n'.join(p['text'] for p in pages.values())
    ocr_tokens=set(re.findall(r'\b\w+\b',ocr_stream))
    page_map = {int(p['printed_page']): p for p in read(ROOT/'sources/page-map.json')['pages']}
    plan_path = DATA/'reconciliation.json'
    plan = read(plan_path) if plan_path.exists() else {}
    aliases = {key(k): v for k, v in plan.get('headword_aliases', {}).items()}
    overrides = plan.get('sense_overrides', {})
    groups = plan.get('sense_groups', {})
    term_overrides = plan.get('term_overrides', {})
    evidence_overrides=plan.get('evidence_overrides',{})
    seen_evidence_refs=set()
    issues = []
    terms = {}
    raw_refs = {}
    reviews = []
    page_reviews = []
    inputs = {}
    readers = []
    names = list(RANGES)
    if (DATA/'readers/coordinator-terms.json').exists():
        names.append('coordinator')
    for name in names:
        path = DATA/f'readers/{name}-terms.json'
        if not path.exists():
            issues.append(f'missing reader return: {name}')
            continue
        payload = read(path); inputs[str(path.relative_to(ROOT))] = sha(path)
        readers.append({'reader': name, 'limits': payload.get('limits', []), 'images_checked': payload.get('images_checked', [])})
        seen_candidates = Counter()
        candidates = {c['id']: c for c in read(DATA/f'{name}-candidates.json')} if name in RANGES else {}
        for review in payload.get('candidate_reviews', []):
            for cid in review['ids']:
                seen_candidates[cid] += 1
                if cid not in candidates:
                    issues.append(f'unknown candidate: {cid}'); continue
                disposition = review['disposition']
                if disposition not in DISPOSITIONS:
                    issues.append(f'unknown disposition: {cid} {disposition}')
                target = review.get('target')
                target = aliases.get(key(target), target) if target else None
                reviews.append(dict(id=cid, reader=name, **{k:v for k,v in candidates[cid].items() if k!='id'},
                    disposition=disposition, target=target, reason=review.get('reason','')))
        for cid, c in candidates.items():
            if seen_candidates[cid] != 1:
                issues.append(f'candidate review count {seen_candidates[cid]}: {cid} {c["form"]}')
        page_reviews.extend(dict(reader=name, **r) for r in payload.get('page_reviews', []))
        if name in RANGES:
            a,b=RANGES[name]; found=Counter(r['page'] for r in payload.get('page_reviews', []))
            if found != Counter(range(a,b+1)):
                issues.append(f'page-review coverage mismatch: {name}')
        for raw in payload.get('terms', []):
            h = aliases.get(key(raw['headword']), raw['headword'])
            tid = 'lex:' + slug(h)
            if tid not in terms:
                terms[tid] = dict(id=tid,headword=h,kind=raw.get('kind','term'),domains=[],roles=[],query_aliases=[],observed_forms=[],senses=[],relations=[],readers=[],scope=raw.get('scope','Grundzüge main text'))
            term = terms[tid]
            if term['headword']!=h:
                issues.append(f'headwords collide without an explicit alias: {term["headword"]} / {h}')
            term['readers'].append(name)
            term['roles'].append(raw.get('role','source terminology or contextual vocabulary'))
            if h!=raw['headword']:term['query_aliases'].append(raw['headword'])
            term['domains'].extend(raw.get('domain',[]) if isinstance(raw.get('domain'),list) else [raw.get('domain','unspecified')])
            term['observed_forms'].extend(raw.get('forms',[]))
            term['relations'].extend(raw.get('relations',[]))
            for n, sense in enumerate(raw.get('senses', []),1):
                ref = f'{name}|{raw["headword"]}|{n}'
                sense = {**sense, **overrides.get(ref,{})}
                group = groups.get(ref, ref)
                existing = next((s for s in term['senses'] if s['group'] == group),None)
                if existing is None:
                    existing = dict(group=group,label=sense['label'],definition=sense['definition'],renderings=sense['renderings'],rule=sense['rule'],caution=sense['caution'],evidence=[],origins=[],uses=[])
                    term['senses'].append(existing)
                elif (existing['definition'],existing['rule']) != (sense['definition'],sense['rule']):
                    # A group has one coordinator definition/rule, supplied explicitly.
                    merged = plan.get('merged_senses',{}).get(group)
                    if not merged:
                        issues.append(f'merged sense needs an explicit synthesis: {group}')
                    else:
                        existing.update(merged)
                existing['origins'].append(ref);raw_refs[ref]=existing
                existing['uses'].append(dict(origin=ref,label=sense['label'],definition=sense['definition'],renderings=sense['renderings'],rule=sense['rule'],caution=sense['caution']))
                for ne,raw_ev in enumerate(sense.get('evidence',[]),1):
                    evidence_ref=ref+f'|{ne}';seen_evidence_refs.add(evidence_ref)
                    ev={**raw_ev,**evidence_overrides.get(evidence_ref,{})}
                    ev['reported_term_form']=raw_ev.get('term_form')
                    ev['evidence_role']=ev.get('evidence_role','direct_occurrence')
                    ev['source_record']=evidence_ref
                    p=ev['printed_page'];path=ev.get('source_path','sources/raw/gs-v-1906.pdf')
                    ev['source_path']=path;ev['source_sha256']=sha(ROOT/path)
                    ev['reader']=name;ev['origin']=ref
                    if path=='sources/raw/gs-v-1906.pdf' and isinstance(p,int) and p in pages:
                        ev['scan_leaf']=page_map[p]['scan_leaf']
                        if ev['pdf_page'] != page_map[p]['pdf_page']:
                            issues.append(f'wrong PDF coordinate: {ref} {p}')
                        try:
                            ev['page_span']=list(span(pages[p]['text'],ev['ocr_quote']))
                        except ValueError as err:
                            issues.append(f'{ref}, p{p}: {err}')
                    if not ev.get('checked_quote'):
                        issues.append(f'unchecked operational evidence: {ref}, p{p}')
                    quote=ev.get('checked_quote') or ev.get('ocr_quote','')
                    form=ev.get('term_form')
                    ev['checked_parts']=[]
                    if ev['evidence_role']=='direct_occurrence':
                        form_match=re.search(r'(?<!\w)'+re.escape(form)+r'(?!\w)',quote,re.I) if form else None
                        if not form_match:issues.append(f'term form not in checked quote: {ref}, {form!r}')
                        else:
                            ev['term_form']=form_match.group()
                            ev['checked_parts']=[dict(text=form_match.group(),span=[form_match.start(),form_match.end()])]
                    elif ev['evidence_role']=='word_part':
                        fragment=ev['fragment']
                        try:
                            a,b=span(quote,fragment);ev['checked_parts']=[dict(text=fragment,span=[a,b])]
                        except ValueError as err:issues.append(f'word part does not anchor: {ref}: {err}')
                    elif ev['evidence_role']=='elliptical_expression':
                        cursor=0
                        for part in ev['expression_parts']:
                            match=re.search(r'(?<!\w)'+re.escape(part)+r'(?!\w)',quote[cursor:],re.I)
                            if not match:issues.append(f'ellipsis part does not anchor: {ref}: {part}');break
                            a=cursor+match.start();b=cursor+match.end();ev['checked_parts'].append(dict(text=quote[a:b],span=[a,b]));cursor=b
                    elif ev['evidence_role']!='supporting_context':issues.append('unknown evidence role: '+evidence_ref)
                    if not ev.get('text_layer'):
                        issues.append(f'no source layer: {ref}')
                    existing['evidence'].append(ev)
                if not existing['evidence']:
                    issues.append(f'unsupported sense: {ref}')
    review_overrides = {x['id']:x for x in plan.get('candidate_overrides',[])}
    for r in reviews:
        r.update({k:v for k,v in review_overrides.get(r['id'],{}).items() if k!='id'})
        if r['disposition']=='needs_review':issues.append('unresolved candidate: '+r['id'])
        if r['disposition']=='included':
            target='lex:'+slug(r['target'] or '')
            if target not in terms:
                issues.append(f'candidate target missing: {r["id"]} {r["target"]}')
            # A surface candidate can name a component of a phrase. Its target
            # association is not automatically a lexical spelling/inflection.
    for ref in set(overrides)|set(groups):
        if ref not in raw_refs:issues.append('reconciliation reference missing: '+ref)
    for ref in evidence_overrides:
        if ref not in seen_evidence_refs:issues.append('evidence reconciliation reference missing: '+ref)
    composites=[]
    for term in terms.values():
        term.update(term_overrides.get(term['headword'],{}))
        term['domains']=sorted(set(term['domains']))
        term['roles']=sorted(set(term['roles']))
        term['query_aliases']=sorted(set(term['query_aliases']),key=lambda x:(x.casefold(),x))
        term['readers']=sorted(set(term['readers']))
        exclusions=plan.get('form_exclusions',{}).get(term['headword'],[])
        term['observed_forms']=sorted(set(term['observed_forms'])-set(exclusions),key=lambda x:(x.casefold(),x))
        for n,sense in enumerate(term['senses'],1):
            sense['id']=term['id']+f':s{n:02}'
            for nu,use in enumerate(sense['uses'],1):use['id']=sense['id']+f':u{nu:02}'
            use_ids={use['origin']:use['id'] for use in sense['uses']}
            for n2,ev in enumerate(sense['evidence'],1):
                ev['id']=sense['id']+f':e{n2:02}';ev['use_id']=use_ids[ev['origin']]
                if ev['evidence_role']=='direct_occurrence':term['observed_forms'].append(ev['term_form'])
        term['observed_forms']=sorted(set(term['observed_forms']),key=lambda x:(x.casefold(),x))
        parts=defaultdict(list)
        for sense in term['senses']:
            for ev in sense['evidence']:
                if ev.get('composite_group'):parts[(sense['id'],ev['composite_group'])].append(ev)
            for use in sense['uses']:
                own=[e for e in sense['evidence'] if e['use_id']==use['id']]
                if not any(e['evidence_role'] in {'direct_occurrence','word_part','elliptical_expression'} for e in own):issues.append('use has only background context: '+use['origin'])
        for (sid,gid),members in parts.items():
            members.sort(key=lambda e:e['part_order'])
            if [e['part_order'] for e in members]!=list(range(1,len(members)+1)) or len(members)<2:
                issues.append('incomplete composite occurrence: '+gid);continue
            joined=''.join(e['fragment'][:-1] if e['fragment'].endswith('-') else e['fragment'] for e in members)
            if key(joined)!=key(term['headword']):issues.append('rejoined compound differs from headword: '+gid)
            composites.append(dict(id=gid,lexeme_id=term['id'],sense_id=sid,joined_form=joined,method='Rejoin explicitly checked print page-end hyphenation; preserve all fragments and locators.',members=[dict(evidence_id=e['id'],order=e['part_order']) for e in members]))
        nonvariants={e['fragment'] for s in term['senses'] for e in s['evidence'] if e['evidence_role']=='word_part'}
        nonvariants|={part for s in term['senses'] for e in s['evidence'] if e['evidence_role']=='elliptical_expression' for part in e['expression_parts']}
        # A lookup form is not automatically a checked print spelling. Preserve
        # that difference, including editorial headwords and OCR-only variants.
        form_records=[]
        for form in sorted(set([term['headword'],*term['observed_forms'],*term['query_aliases']]),key=lambda x:(x.casefold(),x)):
            if form in nonvariants and form!=term['headword']:continue
            pattern=r'(?<!\w)'+re.escape(form)+r'(?!\w)'
            checked=[e['id'] for s in term['senses'] for e in s['evidence'] if e['evidence_role']=='direct_occurrence' and re.search(pattern,e['checked_quote'])]
            in_ocr=form in ocr_tokens if re.fullmatch(r'\w+',form) else bool(re.search(pattern,ocr_stream))
            role='checked_source' if checked else 'ocr_lookup' if in_ocr else 'editorial_lookup'
            if not any(e['evidence_role']=='direct_occurrence' for s in term['senses'] for e in s['evidence']) and any(e['evidence_role']=='elliptical_expression' for s in term['senses'] for e in s['evidence']):role='editorial_ellipsis'
            composite=next((g for g in composites if g['lexeme_id']==term['id'] and key(g['joined_form'])==key(form)),None)
            if composite:role='checked_rejoined';checked=[m['evidence_id'] for m in composite['members']]
            form_records.append(dict(form=form,role=role,evidence_ids=checked))
        term['forms']=form_records
        term['checked_forms']=[x['form'] for x in form_records if x['role'] in {'checked_source','checked_rejoined'}]
        relations=[]
        for rel in term['relations']:
            target=aliases.get(key(rel['target']),rel['target']);target_id='lex:'+slug(target)
            override=plan.get('relation_overrides',{}).get(term['headword']+'|'+target)
            if override:rel={**rel,**override}
            if target_id==term['id']:continue
            if target_id not in terms:
                # Preserve the named comparison as text; no dangling entity FK.
                rel={**rel,'target_label':target,'target_id':None}
            else:rel={**rel,'target_label':target,'target_id':target_id}
            if rel not in relations:relations.append(rel)
        term['relations']=relations
    for rel in plan.get('relations',[]):
        source='lex:'+slug(rel['source']);target='lex:'+slug(rel['target'])
        if source not in terms or target not in terms:
            issues.append(f'curated relation endpoint missing: {rel["source"]} -> {rel["target"]}')
            continue
        terms[source]['relations'].append(dict(type=rel['type'],target_id=target,target_label=terms[target]['headword'],reason=rel['reason']))
    carry=[]
    mapping=plan.get('carry_forward',{})
    for entry in read(ROOT/'sources/terminology/register.json')['entries']:
        for form in entry['forms']:
            m=mapping.get(form)
            if m is None:
                exact=next((t for t in terms.values() if key(form) in {key(t['headword']),*map(key,t['observed_forms'])}),None)
                if exact:m={'target':exact['headword'],'disposition':'term_or_observed_form','reason':'Exact headword/observed-form match; individual sense evidence is independent.'}
            if m is None:
                issues.append(f'original label needs disposition: {form}');continue
            if m.get('target') and 'lex:'+slug(m['target']) not in terms:
                issues.append(f'carry-forward target missing: {form} -> {m["target"]}')
            carry.append(dict(old_entry=entry['id'],old_label=form,**m))
    for name in RANGES:
        p=DATA/f'{name}-candidates.json';inputs[str(p.relative_to(ROOT))]=sha(p)
    for p in [ROOT/'sources/terminology/search-pages.json',ROOT/'sources/page-map.json',plan_path]:
        if p.exists():inputs[str(p.relative_to(ROOT))]=sha(p)
    controls_path=DATA/'comparative-controls.json'
    controls=read(controls_path) if controls_path.exists() else []
    links=[]
    by_headword={key(t['headword']):t['id'] for t in terms.values()}
    for control in controls:
        if control.get('applicable') is False:continue
        for h in control.get('headwords',[]):
            target=by_headword.get(key(h))
            if target:
                links.append(dict(lexeme_id=target,control_id=control['id'],relation='named source comparison',comment='A comparative control for this named term; the individual local sense is supported by its own primary attestation.'))
    for item in plan.get('control_links',[]):
        item=dict(item);target='lex:'+slug(item.pop('headword'))
        if target not in terms:issues.append('manual control target missing: '+target)
        else:
            link=dict(lexeme_id=target,**item)
            links=[x for x in links if (x['lexeme_id'],x['control_id'])!=(link['lexeme_id'],link['control_id'])]
            links.append(link)
    if controls_path.exists():inputs[str(controls_path.relative_to(ROOT))]=sha(controls_path)
    result=dict(schema_version=2,id='grundzuege-termbase-v2',status='candidate assembly' if issues else 'validated source-grounded working termbase',
        terms=sorted(terms.values(),key=lambda t:key(t['headword'])),candidate_reviews=reviews,page_reviews=page_reviews,carry_forward=carry,
        readers=readers,input_sha256=inputs,issues=issues,controls=controls,control_links=links,composite_attestations=composites,
        qualification='Contextual senses/uses are provisional interpretations of cited primary passages. Candidate dispositions do not assign a sense to every OCR occurrence. Image checks are model-assisted, not specialist human validation.')
    if strict and issues:
        raise ValueError('\n'.join(issues[:100])+f'\n{len(issues)} total issues')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--draft',action='store_true');parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=assemble(strict=not args.draft)
    if args.output:
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(terms=len(result['terms']),senses=sum(len(t['senses']) for t in result['terms']),
        evidence=sum(len(s['evidence']) for t in result['terms'] for s in t['senses']),candidates=len(result['candidate_reviews']),
        pages=len(result['page_reviews']),carry_forward=len(result['carry_forward']),issues=result['issues'][:100],issue_count=len(result['issues'])),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
