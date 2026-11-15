"""Real scholarly-data regression; needs durable records, not old holdings."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from humboldt import ingest


class CorpusRegression(unittest.TestCase):
    def test_initial_scholarly_content_matches_approved_baseline(self):
        result=ingest.verify(ROOT,ROOT/'edition/baselines/initial.json')
        self.assertTrue(result['matches'])


if __name__=='__main__':unittest.main()
