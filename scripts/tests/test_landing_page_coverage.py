import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ai_docs_review as review


class LandingPageCoverageTests(unittest.TestCase):
    def setUp(self):
        self.check = review.LandingPageCoverageCheck()
        self.path = review.PROJECT_ROOT / 'docs/tools/example.md'

    def test_missing_metadata_is_high_static_defect(self):
        issues = self.check.run_page(self.path, '---\ntitle: Example\n---\nText')
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]['severity'], 'high')
        self.assertEqual(issues[0]['source'], 'static')
        self.assertIn('sidebar_custom_props.sampleCard', issues[0]['message'])

    def test_current_pages_have_complete_cards(self):
        for section in self.check.sections:
            for path in (review.PROJECT_ROOT / 'docs' / section).rglob('*.md'):
                with self.subTest(path=path):
                    self.assertEqual(self.check.run_page(path, path.read_text()), [])

    def test_drafts_and_landing_pages_are_excluded(self):
        self.assertEqual(self.check.run_page(self.path, '---\ndraft: true\n---\n'), [])
        self.assertEqual(self.check.run_page(self.path.with_name('index.md'), 'Text'), [])

    def test_incomplete_metadata_is_reported(self):
        content = '---\nsidebar_custom_props:\n  sampleCard:\n    tag: Example\n    description: Description\n    highlights: []\n---\n'
        self.assertIn('sampleCard.highlights', self.check.run_page(self.path, content)[0]['message'])

    def test_check_is_in_full_review(self):
        self.assertIn(self.check.name, review.FILTER_PRESETS['full'])
        self.assertTrue(any(isinstance(check, review.LandingPageCoverageCheck)
                            for check in review.build_checks()))
