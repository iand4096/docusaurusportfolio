import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path[:0] = [str(Path(__file__).resolve().parents[1])]
import ai_docs_review as review
from test_qa_report_feedback import finding


class ExampleReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.metadata = {'report_run_at_display': '16 November 2026',
            'report_time_zone': 'Europe/London', 'mode': 'per-page',
            'filter_label': 'Full review', 'model': 'test', 'ai_review_policy_version': 'test',
            'files_reviewed': 1, 'checks': [check.name for check in review.build_checks()]}

    def render(self, count):
        issues = [finding(str(i)) for i in range(count)]
        ci = review.evaluate_ci(issues, [], 0, 5, 0)
        original_ci = copy.deepcopy(ci)
        with patch.object(review, 'REPORT', self.root / 'real.html'), \
             patch.object(review, 'JSON_REPORT', self.root / 'real.json'), \
             patch.object(review, 'MARKDOWN_REPORT', self.root / 'real.md'), \
             patch.object(review, 'request_review', side_effect=AssertionError('No API calls')):
            review.generate_html_report(issues, [], self.metadata, ci)
        self.assertEqual(ci, original_ci)
        return (self.root / 'real.html').read_text()

    def test_quiet_report_generates_separate_labelled_example(self):
        real = self.render(0)
        self.assertIn('See example QA report with errors', real)
        example = (self.root / 'qa-example.html').read_text()
        self.assertIn('href="./real.html">← Back to actual QA report</a>', example)
        self.assertNotIn('Back to Portfolio', example)
        self.assertIn('Back to Portfolio', real)
        self.assertIn('Demonstration only — synthetic findings', example)
        self.assertIn('<small>revision unavailable</small>', example)
        self.assertNotIn('<small>revision una</small>', example)
        self.assertIn('Simulated check failure', example)
        self.assertNotIn('class="challenge-button"', example)
        self.assertNotIn('class="report-actions"', example)
        self.assertNotIn('rel="alternate"', example)
        self.assertNotIn('See example QA report with errors', example)
        self.assertNotIn('github.com/', example)
        self.assertNotIn('Synthetic example document', real)
        data = example.split('<script id="qa-report-data" type="application/json">\n')[1].split('</script>')[0]
        payload = json.loads(data)
        self.assertTrue(payload['metadata']['example_report'])
        self.assertEqual({i['source'] for i in payload['issues']},
                         {'ai', 'static', 'vale', 'ltex', 'lychee', 'remark'})
        self.assertFalse(payload['ci']['passed'])
        self.assertEqual(len(payload['errors']), 1)
        self.assertFalse((self.root / 'qa-example.json').exists())

    def test_threshold_is_inclusive_and_busy_report_omits_offer(self):
        self.assertIn('See example QA report with errors', self.render(5))
        self.assertNotIn('See example QA report with errors', self.render(6))

    def test_example_returns_to_custom_output_filename(self):
        review.generate_html_report([], [], self.metadata,
            review.evaluate_ci([], [], 0, 5, 0),
            output_path=self.root / 'custom report.html')
        example = (self.root / 'qa-example.html').read_text()
        self.assertIn('href="./custom%20report.html">← Back to actual QA report</a>', example)

    def test_standalone_example_returns_to_default_report(self):
        review.generate_example_report(self.root, self.metadata)
        example = (self.root / 'qa-example.html').read_text()
        self.assertIn(f'href="./{review.REPORT.name}">← Back to actual QA report</a>', example)

    def test_history_does_not_hide_example_offer(self):
        issues = [finding(str(i)) for i in range(8)]
        for issue in issues:
            issue['human_resolution'] = 'dismissed'
        self.assertIn('See example QA report with errors', review.example_report_notice(issues, {}))


if __name__ == '__main__':
    unittest.main()
