import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ai_docs_review as review
from qa_review_cache import ReviewCache


class ReviewCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cache = ReviewCache(self.root / 'cache')
        self.issue = dict(source='ai', file='example.md', line=1, original='Text.',
                          message='Problem.', suggestion='Correction.', severity='low',
                          confidence='high', type='improvement', category='clarity')

    def test_hit_skips_compute_and_returns_unmodified_findings(self):
        compute = Mock(return_value=[self.issue])
        self.cache.run({'source': 'Text.'}, compute)
        result = self.cache.run({'source': 'Text.'}, compute)
        result[0]['human_resolution'] = 'dismissed'
        again = self.cache.run({'source': 'Text.'}, compute)
        self.assertNotIn('human_resolution', again[0])
        self.assertEqual(compute.call_count, 1)

    def test_empty_results_cached_but_exceptions_retried(self):
        compute = Mock(return_value=[])
        self.assertEqual(self.cache.run({'source': 'clean'}, compute), [])
        self.assertEqual(self.cache.run({'source': 'clean'}, compute), [])
        self.assertEqual(compute.call_count, 1)
        broken = Mock(side_effect=RuntimeError('Provider unavailable'))
        for _ in range(2):
            with self.assertRaises(RuntimeError):
                self.cache.run({'source': 'broken'}, broken)
        self.assertEqual(broken.call_count, 2)

    def test_corrupt_entry_is_a_miss(self):
        compute = Mock(return_value=[self.issue])
        self.cache.run({}, compute)
        path = next((self.root / 'cache').glob('*.json'))
        path.write_text('{broken')
        self.cache.run({}, compute)
        entry = json.loads(path.read_text())
        entry['findings'][0]['message'] = 'Changed'
        path.write_text(json.dumps(entry))
        self.cache.run({}, compute)
        self.assertEqual(compute.call_count, 3)

    def test_bypass_neither_reads_nor_writes(self):
        compute = Mock(return_value=[])
        disabled = ReviewCache(self.root / 'disabled', enabled=False)
        disabled.run({}, compute)
        disabled.run({}, compute)
        self.assertEqual(compute.call_count, 2)
        self.assertFalse(disabled.directory.exists())

    def test_inputs_bind_path_content_model_check_policy_and_entire_site(self):
        check = Mock(source='ai')
        check.name = 'GrammarReview'
        compute = Mock(return_value=[])
        with patch.object(review, 'PROJECT_ROOT', self.root):
            def run(sources=None, scope='per-page'):
                return review.cached_ai_check(check, sources or {'a.md': 'Text'}, scope, compute)
            run(); run()
            self.assertEqual(compute.call_count, 1)
            run({'a.md': 'Changed'})
            run({'renamed.md': 'Text'})
            with patch.object(review, 'MODEL', 'different-model'):
                run()
            with patch.object(review, 'AI_REVIEW_POLICY_VERSION', 'new-policy'):
                run()
            check.name = 'StructureReview'
            run()
            run({'a.md': 'Text', 'b.md': 'Second'}, 'site-wide')
            run({'a.md': 'Text', 'b.md': 'Updated'}, 'site-wide')
            self.assertEqual(compute.call_count, 8)

    def test_per_page_hit_skips_review_and_verification_calls(self):
        path = self.root / 'example.md'
        path.write_text('Text.')
        raw = dict(self.issue, reader_impact='Concrete consequence.', rule_basis='Clarity',
                   evidence=[{'file': str(path), 'quote': 'Text.'}])
        with patch.object(review, 'PROJECT_ROOT', self.root), patch.object(review, 'request_review',
                side_effect=[{'issues': [raw]}, {'assessments': [dict(index=0, supported=True,
                              reason='Source supports the finding.')]}]) as request:
            first, errors = review.run_per_page_checks([path], [review.GrammarReview()], 'unused')
            second, errors2 = review.run_per_page_checks([path], [review.GrammarReview()], 'unused')
        self.assertEqual(errors + errors2, [])
        self.assertEqual(len(first), 1)
        self.assertEqual(first, second)
        self.assertEqual(request.call_count, 2)

    def test_malformed_review_is_reported_and_retried_before_caching_clean_result(self):
        path = self.root / 'example.md'
        path.write_text('Text.')
        responses = [[], {}, {'issues': None}, {'issues': [None]}, {'issues': []}]
        with patch.object(review, 'PROJECT_ROOT', self.root), patch.object(
            review, 'request_review', side_effect=responses
        ) as request:
            def run():
                return review.run_per_page_checks([path], [review.GrammarReview()], 'unused')

            for response in responses[:-1]:
                with self.subTest(response=response):
                    issues, errors = run()
                    self.assertEqual(issues, [])
                    self.assertEqual(len(errors), 1)
                    self.assertIn('Invalid AI review response', errors[0]['error'])
            self.assertEqual(run(), ([], []))
            self.assertEqual(run(), ([], []))
            self.assertEqual(request.call_count, len(responses))

    def test_deterministic_checks_are_never_cached(self):
        check = Mock(source='vale', name='Vale')
        compute = Mock(return_value=[])
        for _ in range(2):
            review.cached_ai_check(check, {}, 'per-page', compute)
        self.assertEqual(compute.call_count, 2)

    def test_cli_bypass(self):
        with patch.object(sys, 'argv', ['ai_docs_review.py', '--no-review-cache']):
            self.assertTrue(review.parse_args().no_review_cache)


if __name__ == '__main__':
    unittest.main()
