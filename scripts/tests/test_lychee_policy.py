import json
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ai_docs_review as review
from qa_reporting import Report, generate_json_report

PROJECT = Path(__file__).resolve().parents[2]


class LycheePolicyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'article.md'
        self.url = 'https://example.com/reference'
        self.path.write_text(f'# Article\n\n[Reference]({self.url})\n', encoding='utf-8')

    def output(self, status, key='error_map'):
        return json.dumps({key: {str(self.path): [{'url': self.url, 'status': status}]}})

    def finding(self, code, key='error_map'):
        return review.parse_lychee_json(self.output({
            'code': code, 'text': f'Rejected status code: {code}',
        }, key), [self.path])[0]

    def ci(self, issues):
        return review.evaluate_ci(issues, [], fail_high=0, fail_medium=0, fail_api_errors=0)

    def test_rate_limit_and_all_server_errors_are_visible_nonblocking_warnings(self):
        for code in [429, *range(500, 600)]:
            with self.subTest(code=code):
                issue = self.finding(code)
                self.assertEqual((issue['severity'], issue['type'], issue['category']),
                                 ('low', 'improvement', 'external-link-temporary'))
                self.assertIn('temporarily unavailable', issue['message'])
                self.assertIn(f'HTTP {code}', issue['message'])
                self.assertEqual((issue['source'], issue['original'], issue['line']),
                                 ('lychee', self.url, 3))
                self.assertTrue(self.ci([issue])['passed'])

    def test_access_restrictions_require_review_without_asserting_a_broken_link(self):
        for code in [401, 403]:
            with self.subTest(code=code):
                issue = self.finding(code)
                self.assertEqual((issue['severity'], issue['type'], issue['category']),
                                 ('low', 'improvement', 'external-link-access'))
                self.assertIn('requires review', issue['message'])
                self.assertIn(f'HTTP {code}', issue['message'])
                self.assertIn('manually', issue['suggestion'])
                self.assertTrue(self.ci([issue])['passed'])

    def test_not_found_gone_and_other_unclassified_responses_remain_defects(self):
        for code in [400, 404, 405, 408, 410, 499]:
            with self.subTest(code=code):
                issue = self.finding(code)
                self.assertEqual((issue['severity'], issue['type'], issue['category']),
                                 ('high', 'defect', 'external-link'))
                self.assertIn(f'HTTP {code}', issue['message'])
                self.assertFalse(self.ci([issue])['passed'])

    def test_mixed_results_keep_warnings_but_gate_only_on_actual_defects(self):
        issues = [self.finding(code) for code in [429, 503, 401, 403, 404, 410]]
        ci = self.ci(issues)
        self.assertEqual(len(issues), 6)
        self.assertEqual((ci['high_count'], ci['medium_count']), (2, 0))
        self.assertFalse(ci['passed'])
        self.assertTrue(self.ci(issues[:4])['passed'])

    def test_transport_or_unknown_errors_are_not_silently_downgraded(self):
        for status in [None, {'text': 'DNS lookup failed'}, {'code': -1},
                       {'code': True}, 'Connection timed out after 503 milliseconds']:
            with self.subTest(status=status):
                issue = review.parse_lychee_json(self.output(status), [self.path])[0]
                self.assertEqual(issue['severity'], 'high')
                self.assertFalse(self.ci([issue])['passed'])

    def test_explicit_legacy_status_text_and_string_codes_are_classified(self):
        for status, category in [
            ('Rejected status code: 503 Service Unavailable', 'external-link-temporary'),
            ('HTTP 429', 'external-link-temporary'),
            ({'code': '403', 'text': 'Forbidden'}, 'external-link-access'),
        ]:
            with self.subTest(status=status):
                issue = review.parse_lychee_json(self.output(status), [self.path])[0]
                self.assertEqual(issue['category'], category)
                self.assertEqual(issue['severity'], 'low')
        self.assertEqual(self.finding(503, 'fail_map')['category'], 'external-link-temporary')

    def test_invalid_checker_output_remains_a_check_error(self):
        for output in ['invalid JSON', '[]', '{"error_map": []}']:
            with self.subTest(output=output):
                with self.assertRaises(RuntimeError):
                    review.parse_lychee_json(output, [self.path])

    def test_lychee_link_failure_exit_is_parsed_but_runtime_failures_raise(self):
        result = subprocess.CompletedProcess([], 2, self.output({'code': 503}), '')
        with patch.object(review.subprocess, 'run', return_value=result) as run:
            issues = review.LycheeCheck().run_files([self.path], executable='lychee')
            self.assertTrue(self.ci(issues)['passed'])
            command = run.call_args.args[0]
            self.assertNotIn('--accept', command)
            self.assertEqual(run.call_args.kwargs['input'], str(self.path) + '\n')
        for code in [1, 3]:
            with self.subTest(code=code), patch.object(review.subprocess, 'run',
                    return_value=subprocess.CompletedProcess([], code, '', 'invalid configuration')):
                with self.assertRaises(RuntimeError):
                    review.LycheeCheck().run_files([self.path], executable='lychee')

    def test_retry_configuration_remains_enabled_without_accepting_failures(self):
        config = tomllib.loads((PROJECT / 'lychee.toml').read_text())
        self.assertEqual(config['max_retries'], 5)
        self.assertEqual(config['retry_wait_time'], 2)
        self.assertNotIn('accept', config)

    def test_json_report_preserves_warning_statuses(self):
        issues = [self.finding(code) for code in [503, 403, 404]]
        target = Path(self.directory.name) / 'report.json'
        generate_json_report(Report(issues, [], {}, self.ci(issues)), target)
        report = json.loads(target.read_text())
        self.assertEqual(report['ci']['high_count'], 1)
        self.assertEqual(len(report['issues']), 3)
        self.assertTrue(any('HTTP 503' in item['message'] and item['severity'] == 'low'
                            for item in report['issues']))


if __name__ == '__main__':
    unittest.main()
