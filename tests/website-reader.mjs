import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const code = await readFile(new URL('../tools/website/reader.js', import.meta.url), 'utf8');
const { searchRecords, readingLocation } = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);
const records = [
  { title: 'Sound system · 62a', text: 'p62a Tongue and language. Eigenthümlichkeit.', href: '/humboldt/sound-system/#p62a' },
  { title: 'A source note', text: 'Vowel quantity and accent.', href: '/humboldt/sound-system/#note-test' }
];

test('search covers German, case and multiple terms', () => {
  assert.equal(searchRecords(records, 'EIGENTHÜMLICHKEIT tongue').results[0].href, records[0].href);
  assert.equal(searchRecords(records, '62a').total, 1);
  assert.equal(searchRecords(records, 'not-present').total, 0);
});
test('empty and regex-shaped input stay literal', () => {
  assert.deepEqual(searchRecords(records, '   '), { total: 0, results: [] });
  assert.equal(searchRecords(records, '.*').total, 0);
  assert.equal(searchRecords(records, '[a-z]').total, 0);
});
test('truncation preserves the full result count', () => {
  assert.equal(searchRecords(records, 'a', 1).total, 2);
  assert.equal(searchRecords(records, 'a', 1).results.length, 1);
});
test('resume accepts lettered paragraphs and only known reader routes', () => {
  assert.equal(readingLocation('/humboldt/sound-system/', '#p62a', ['sound-system']), '/humboldt/sound-system/#p62a');
  for (const [path, hash] of [['/outside/', '#p1'], ['/humboldt/unknown/', '#p1'], ['/humboldt/sound-system/', '#note-test'], ['/humboldt/sound-system/', '#p62aa']]) {
    assert.equal(readingLocation(path, hash, ['sound-system']), null);
  }
});
