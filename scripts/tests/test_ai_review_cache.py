import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ai_docs_review as review
from qa_ai import cache, client
from qa_ai.cache import AIReviewCache
from qa_ai.checks import GrammarReview
from qa_checks.base import BaseCheck, CheckResult
from qa_runner import CheckPlan, run_checks
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
        check = Mock(source='ai', defects_only=False)
        check.name = 'GrammarReview'
        compute = Mock(return_value=[])
        ai_cache = AIReviewCache(self.root / 'review')
        def run(sources=None, scope='per-page'):
            return ai_cache.run(check, sources or {'a.md': 'Text'}, scope, compute)
        run(); run()
        self.assertEqual(compute.call_count, 1)
        run({'a.md': 'Changed'})
        run({'renamed.md': 'Text'})
        with patch.object(client, 'MODEL', 'different-model'):
            run()
        with patch.object(cache, 'AI_REVIEW_POLICY_VERSION', 'new-policy'):
            run()
        check.name = 'StructureReview'
        run()
        run({'a.md': 'Text', 'b.md': 'Second'}, 'site-wide')
        run({'a.md': 'Text', 'b.md': 'Updated'}, 'site-wide')
        self.assertEqual(compute.call_count, 8)

    def test_per_page_hit_skips_review_and_verification_calls(self):
        path = self.root / 'example.md'
        path.write_text('Text.')
        plan = CheckPlan.for_mode('per-page', [GrammarReview()])
        ai_cache = AIReviewCache(self.root / 'review')
        raw = dict(self.issue, reader_impact='Concrete consequence.', rule_basis='Clarity',
                   evidence=[{'file': str(path), 'quote': 'Text.'}])
        with patch.object(client, 'request_review',
                side_effect=[{'issues': [raw]}, {'assessments': [dict(index=0, supported=True,
                              reason='Source supports the finding.')]}]) as request:
            first = run_checks([path], plan, 'unused', cached_check=ai_cache.run)
            second = run_checks([path], plan, 'unused', cached_check=ai_cache.run)
        self.assertEqual(first.errors + second.errors, [])
        self.assertEqual(len(first.issues), 1)
        self.assertEqual(first, second)
        self.assertEqual(request.call_count, 2)

    def test_malformed_review_is_reported_and_retried_before_caching_clean_result(self):
        path = self.root / 'example.md'
        path.write_text('Text.')
        plan = CheckPlan.for_mode('per-page', [GrammarReview()])
        ai_cache = AIReviewCache(self.root / 'review')
        responses = [[], {}, {'issues': None}, {'issues': [None]}, {'issues': []}]
        with patch.object(
            client, 'request_review', side_effect=responses
        ) as request:
            def run():
                return run_checks([path], plan, 'unused', cached_check=ai_cache.run)

            for response in responses[:-1]:
                with self.subTest(response=response):
                    result = run()
                    self.assertEqual(result.issues, [])
                    self.assertEqual(len(result.errors), 1)
                    self.assertIn('Invalid AI review response', result.errors[0]['error'])
            self.assertEqual(run(), CheckResult())
            self.assertEqual(run(), CheckResult())
            self.assertEqual(request.call_count, len(responses))

    def test_prompt_changes_invalidate_cache_but_report_template_changes_do_not(self):
        package = self.root / 'qa_ai'
        package.mkdir()
        prompt = package / 'prompts.py'
        prompt.write_text('PROMPT = "Original"')
        reporting = self.root / 'qa_reporting'
        reporting.mkdir()
        template = reporting / 'report.html'
        template.write_text('<p>Original report</p>')
        check = GrammarReview()
        compute = Mock(return_value=[])
        with patch.object(cache, 'PACKAGE_DIR', package):
            def run():
                return AIReviewCache(self.root / 'review').run(
                    check, {'a.md': 'Text.'}, 'per-page', compute)

            run()
            template.write_text('<p>Updated report</p>')
            run()
            self.assertEqual(compute.call_count, 1)
            prompt.write_text('PROMPT = "Updated"')
            run()
            self.assertEqual(compute.call_count, 2)

    def test_combined_plan_reads_source_once_and_reuses_it_for_both_scopes(self):
        path = self.root / 'example.md'
        path.write_text('Original.')
        check = Mock(spec=BaseCheck, name='BothScopes')
        check.name = 'BothScopes'
        check.source = 'static'
        check.supports_page = check.supports_site = True
        check.run_page.return_value = []
        check.run_site.return_value = []
        plan = CheckPlan.for_mode('all', [check])
        ai_cache = AIReviewCache(self.root / 'review')
        read_text = Path.read_text
        with patch.object(Path, 'read_text', autospec=True, side_effect=read_text) as read:
            result = run_checks([path], plan, None, cached_check=ai_cache.run)
        read.assert_called_once_with(path, encoding='utf-8')
        check.run_page.assert_called_once_with(path, 'Original.', None)
        check.run_site.assert_called_once_with([path], {path.as_posix(): 'Original.'}, None)
        self.assertEqual(plan.checks, [check])
        self.assertEqual(result, CheckResult())

    def test_deterministic_checks_are_never_cached(self):
        check = Mock(source='vale', name='Vale')
        compute = Mock(return_value=[])
        for _ in range(2):
            AIReviewCache(self.root / 'review').run(check, {}, 'per-page', compute)
        self.assertEqual(compute.call_count, 2)

    def test_cli_bypass(self):
        with patch.object(sys, 'argv', ['ai_docs_review.py', '--no-review-cache']):
            self.assertTrue(review.parse_args().no_review_cache)


if __name__ == '__main__':
    unittest.main()
