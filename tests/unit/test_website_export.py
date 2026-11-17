"""A stale note must never silently attach to a new website translation."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('website_export', ROOT / 'tools/export_website.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WebsiteAttachment(unittest.TestCase):
    def setUp(self):
        self.version = dict(id='en-fake-v1', body='First. Second thought.', body_sha256='frozen')
        self.unit = dict(start=7, end=22, version_id='en-fake-v1')
        self.note = dict(id='fake-note', target_version='en-fake-v1', target_body_sha256='frozen', anchor=dict(offset_in_rendering=6, after='Second'))

    def test_rendering_offset_is_converted_to_body_offset(self):
        self.assertEqual(module.check_anchor(self.note, self.version, self.unit), 13)

    def test_changed_body_or_version_requires_reattachment(self):
        for field in ['id', 'body_sha256']:
            changed = dict(self.version, **{field:'changed'})
            with self.assertRaisesRegex(ValueError, 'semantic reattachment'):
                module.check_anchor(self.note, changed, self.unit)
        with self.assertRaisesRegex(ValueError, 'semantic reattachment'):
            module.check_anchor(self.note, self.version, dict(self.unit, version_id='wrong-version'))

    def test_same_offset_with_different_words_is_rejected(self):
        changed = dict(self.version, body='First. Altered thought.')
        with self.assertRaisesRegex(ValueError, 'anchor differs'):
            module.check_anchor(self.note, changed, self.unit)
        invalid = deepcopy(self.note)
        invalid['anchor']['offset_in_rendering'] = 99
        with self.assertRaisesRegex(ValueError, 'outside rendering'):
            module.check_anchor(invalid, self.version, self.unit)


if __name__ == '__main__':
    unittest.main()
