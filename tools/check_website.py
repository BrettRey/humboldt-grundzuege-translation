#!/usr/bin/env python3
"""Check the static reader's content preservation, links and note attachment."""
import argparse
from collections import Counter
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


class Element:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def all(self, test):
        result = [self] if test(self) else []
        for child in self.children:
            if isinstance(child, Element):
                result.extend(child.all(test))
        return result

    def text(self, skip_sup=False):
        if skip_sup and self.tag == 'sup':
            return ''
        return ''.join(c.text(skip_sup) if isinstance(c, Element) else c for c in self.children)

    def has_class(self, name):
        return name in self.attrs.get('class', '').split()


class Document(HTMLParser):
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.root = Element()
        self.stack = [self.root]
        self.feed(text)
        assert len(self.stack) == 1, 'Unclosed HTML elements'

    def handle_starttag(self, tag, attrs):
        node = Element(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        assert self.stack[-1].tag == tag, (tag, self.stack[-1].tag)
        self.stack.pop()

    def handle_data(self, data):
        self.stack[-1].children.append(data)

    def all(self, test):
        return self.root.all(test)


def normal(text):
    return ' '.join(text.split())


def check(output, website=None):
    output = output.resolve()
    website = website.resolve() if website else output.parent
    snapshot = json.loads((output / 'snapshot.json').read_text())
    for file in snapshot['files']:
        assert hashlib.sha256((output / file['path']).read_bytes()).hexdigest() == file['sha256'], file['path']
    documents = {p: Document(p.read_text()) for p in output.rglob('*.html')}
    ids = {}
    for path, doc in documents.items():
        values = [n.attrs['id'] for n in doc.all(lambda n: 'id' in n.attrs)]
        assert len(values) == len(set(values)), ('Duplicate id', path)
        ids[path] = set(values)
    def local_target(href, page):
        value = urlsplit(href)
        if value.scheme in {'https', 'http', 'mailto'}:
            return
        assert not value.scheme and not value.netloc, ('Unsafe URL', href)
        target = ((website / unquote(value.path).lstrip('/')) if value.path.startswith('/') else (page.parent / unquote(value.path))) if value.path else page
        target = target.resolve()
        if target.is_dir():
            target /= 'index.html'
        assert target.is_relative_to(website), ('Link leaves website', href)
        assert target.exists(), ('Missing local target', page, href, target)
        if value.fragment:
            assert target in ids and unquote(value.fragment) in ids[target], ('Missing fragment', page, href)
    local_links = 0
    for path, doc in documents.items():
        for node in doc.all(lambda n: 'href' in n.attrs or 'src' in n.attrs):
            url = node.attrs.get('href', node.attrs.get('src'))
            local_target(url, path)
            local_links += not bool(urlsplit(url).scheme)
        assert doc.all(lambda n: n.tag == 'html')[0].attrs['lang'] == 'en'
        assert doc.all(lambda n: n.tag == 'meta' and n.attrs.get('name') == 'viewport')
    passage_count = note_count = 0
    authors = Counter()
    for section in snapshot['sections']:
        folder = output / section['slug']
        data = json.loads((folder / 'records.json').read_text())
        doc = documents[folder / 'index.html']
        passages = doc.all(lambda n: n.tag == 'article' and n.has_class('passage'))
        assert [n.text() for n in doc.all(lambda n: n.has_class('printed-heading'))] == [h['text'] for h in data['headings']]
        assert [n.attrs['id'] for n in passages] == ['p' + p['number'] for p in data['paragraphs']]
        for paragraph, node in zip(data['paragraphs'], passages):
            en = node.all(lambda n: n.has_class('english'))[0]
            assert normal(en.text(skip_sup=True)) == normal(paragraph['english']), ('English changed', paragraph['number'])
            assert len(en.all(lambda n: n.tag == 'p')) == len(paragraph['english_groups']), ('Printed English breaks changed', paragraph['number'])
            de = node.all(lambda n: n.has_class('german'))[0]
            source = de.all(lambda n: n.tag == 'p' and not n.has_class('source-links'))
            assert normal(' '.join(p.text() for p in source)) == normal(paragraph['german']), ('German changed', paragraph['number'])
            assert len(source) == len(paragraph['german_groups'])
            for key, language in [('target_sha256', 'english'), ('source_sha256', 'german')]:
                assert hashlib.sha256(paragraph[language].encode()).hexdigest() == paragraph[key]
            assert node.all(lambda n: n.tag == 'a' and 'archive.org/download/' in n.attrs.get('href', ''))
        calls = doc.all(lambda n: n.has_class('note-ref'))
        assert [n.attrs['href'] for n in calls] == ['#note-' + n['id'] for n in data['notes']], ('Note order differs', section['slug'])
        assert [n.text() for n in calls] == [str(i) for i in range(1, len(calls) + 1)]
        for note in data['notes']:
            li = doc.all(lambda n: n.attrs.get('id') == 'note-' + note['id'])[0]
            assert li.tag == 'li' and li.attrs['data-number'] == str(note['display_number'])
            assert '(' + note['attribution'] + ')' in li.text()
            authors[note['attribution']] += 1
        passage_count += len(passages)
        note_count += len(calls)
    index = json.loads((output / 'search-index.json').read_text())
    for row in index:
        local_target(row['href'], output / 'index.html')
    assert not any('file://' in p.read_text() or '{>>' in p.read_text() or '{~~' in p.read_text() for p in documents), 'Private file link or review markup published'
    result = dict(sections=len(snapshot['sections']), passages=passage_count, notes=note_count, note_authorship=dict(authors), local_links=local_links, search_records=len(index), all_bodies_preserved=True, all_local_links_resolve=True, unique_ids=True, all_note_sequences_and_targets_valid=True, browser_interactions='Require separate browser QA; these are structural and content checks.')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--website', type=Path)
    args = parser.parse_args()
    check(args.output, args.website)
