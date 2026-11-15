#!/usr/bin/env python3
"""Reproduce the deliberately broad terminology-review inventory from source OCR."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re

import alignment_store as store

ROOT=store.ROOT
RANGES={'early':(364,399),'middle':(400,444),'late':(445,473)}
TECHNICAL=re.compile(r'^(?:objectiv|subjectiv|sinnlich|geistig|intellect|logisch|grammatisch|lexical|phonet|formal|formell|ideal|organisch|mechanisch|synthet|analyt|articul|artikul|einverleib|agglutin|isolir|isolier|flex|symbol|bezeichn|hinzudenk|bildsam|willkühr|willkür|ursprüng)')


def inventory(pages,a,b,name):
    tokens=defaultdict(list)
    for page in pages:
        if not a<=page['printed_page']<=b:continue
        for start,end in store.word_spans(page['text']):
            word=page['text'][start:end]
            capital=bool(re.fullmatch(r'[A-ZÄÖÜ][A-Za-zÄÖÜäöüß]+',word)) and len(word)>2
            if capital or TECHNICAL.search(word.casefold()):
                tokens[word].append((page['printed_page'],'header_candidate' if start<page['header_end'] else 'body_or_note'))
    result=[]
    for n,word in enumerate(sorted(tokens,key=str.casefold),1):
        occurrences=tokens[word]
        result.append(dict(id=f'{name}:{n:04}',form=word,count=len(occurrences),pages=sorted({p for p,z in occurrences}),header_only=all(z=='header_candidate' for p,z in occurrences)))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    if any((a.output/f'{name}-candidates.json').exists() for name in RANGES):parser.error('choose a fresh output directory')
    pages=json.loads((ROOT/'sources/terminology/search-pages.json').read_text())
    for name,(first,last) in RANGES.items():
        result=inventory(pages,first,last,name)
        (a.output/f'{name}-candidates.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        rows=['id\tform\tcount\tprinted_pages\theader_only']+[f"{x['id']}\t{x['form']}\t{x['count']}\t{','.join(map(str,x['pages']))}\t{x['header_only']}" for x in result]
        (a.output/f'{name}-candidates.tsv').write_text('\n'.join(rows)+'\n')
        print(name,len(result))


if __name__=='__main__':main()
