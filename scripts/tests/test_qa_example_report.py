import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path[:0] = [str(Path(__file__).resolve().parents[1])]
import ai_docs_review as review
from qa_ai import client
from qa_reporting import Report, ReportPaths
from qa_reporting.html_report import example_report_notice, generate_example_report, generate_html_report
from test_qa_report_feedback import finding


class ExampleReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.check_sources = {check.name: check.source for check in review.build_checks()}
        self.metadata = {'report_run_at_display': '16 November 2026',
            'report_time_zone': 'Europe/London', 'mode': 'per-page',
            'filter_label': 'Full review', 'model': 'test', 'ai_review_policy_version': 'test',
            'files_reviewed': 1, 'checks': list(self.check_sources)}

    def render(self, count):
        issues = [finding(str(i)) for i in range(count)]
        ci = review.evaluate_ci(issues, [], 0, 5, 0)
        original_ci = copy.deepcopy(ci)
        paths = ReportPaths(self.root / 'real.html', self.root / 'real.json', self.root / 'real.md')
        with patch.object(client, 'request_review', side_effect=AssertionError('No API calls')):
            generate_html_report(Report(issues, [], self.metadata, ci), paths, self.check_sources)
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

    def test_tooltip_occurrence_displays_match_and_canonical_term(self):
        issue = finding('tooltip')
        issue.update(source='tooltip', category='tooltip-mention', tooltip_evidence={
            'matched_text': 'requests <example>', 'label': 'Requests', 'term_id': 'requests',
        })
        paths = ReportPaths.in_directory(self.root)
        ci = review.evaluate_ci([issue], [], 0, 5, 0)
        generate_html_report(Report([issue], [], self.metadata, ci), paths, self.check_sources)
        self.assertIn('Matched <q>requests &lt;example&gt;</q> · '
                      'Tooltip <q>Requests</q> (<code>requests</code>)', paths.html.read_text())

    def test_example_returns_to_custom_output_filename(self):
        defaults = ReportPaths.in_directory(self.root)
        paths = ReportPaths(self.root / 'custom report.html', defaults.json, defaults.markdown)
        generate_html_report(Report([], [], self.metadata, review.evaluate_ci([], [], 0, 5, 0)),
                             paths, self.check_sources)
        example = (self.root / 'qa-example.html').read_text()
        self.assertIn('href="./custom%20report.html">← Back to actual QA report</a>', example)

    def test_standalone_example_returns_to_default_report(self):
        paths = ReportPaths.in_directory(self.root)
        generate_example_report(paths, self.metadata, self.check_sources)
        example = (self.root / 'qa-example.html').read_text()
        self.assertIn(f'href="./{paths.html.name}">← Back to actual QA report</a>', example)

    def test_history_does_not_hide_example_offer(self):
        issues = [finding(str(i)) for i in range(8)]
        for issue in issues:
            issue['human_resolution'] = 'dismissed'
        self.assertIn('See example QA report with errors', example_report_notice(issues, {}))


if __name__ == '__main__':
    unittest.main()
