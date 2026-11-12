import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ai_docs_review as review
import qa_feedback as feedback


def finding(name, source='ai'):
    return {
        'issue_id': 'qa-' + name, 'file': 'README.md', 'line': 3,
        'severity': 'medium', 'confidence': 'high', 'type': 'defect',
        'category': 'clarity', 'source': source, 'original': 'Source passage',
        'message': 'Original criticism ' + name, 'suggestion': 'Original suggestion',
        'document_revision': {'content_sha256': 'a' * 64},
    }


def feedback_record(issue, decision=None, pending=False, dismissed=False):
    return {
        'latest_finding': copy.deepcopy(issue),
        'status': 'challenged' if pending else 'adjudicated',
        'human_resolution': 'dismissed' if dismissed else None,
        'discussion': [{'role': 'human', 'text': 'Rebuttal <script>unsafe()</script>'}],
        'adjudications': [{
            'decision': decision, 'reason': 'Reason with evidence',
            'evidence': ['Source passage'], 'document_revision': issue['document_revision'],
            'revised_message': 'Revised criticism' if decision == 'revised' else None,
            'revised_suggestion': 'Revised suggestion' if decision == 'revised' else None,
        }] if decision else [],
    }


class ReportFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='report-feedback-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.feedback = self.root / 'feedback.json'

    def attach(self, issues, records):
        self.feedback.write_text(json.dumps({'schema_version': 1, 'records': records}))
        feedback.attach_feedback_status(issues, self.feedback)

    def test_decisions_pending_and_ci_policy(self):
        issues = [finding(name) for name in ('new', 'pending', 'withdrawn', 'upheld',
                                           'revised', 'needs_evidence', 'dismissed')]
        issues.append(finding('static', 'vale'))
        records = {i['issue_id']: feedback_record(i, i['issue_id'][3:]) for i in issues[2:6]}
        records['qa-pending'] = feedback_record(issues[1], 'withdrawn', pending=True)
        records['qa-dismissed'] = feedback_record(issues[6], 'withdrawn', dismissed=True)
        records['qa-static'] = feedback_record(issues[7], 'withdrawn', dismissed=True)
        self.attach(issues, records)
        counts = review.report_counts(issues)
        self.assertEqual((counts['active'], counts['history'], counts['pending']), (6, 2, 1))
        self.assertEqual(review.feedback_state(issues[1]), 'challenged')
        self.assertFalse(review.is_history_issue(issues[1]))
        self.assertEqual(issues[4]['effective_message'], 'Revised criticism')
        self.assertEqual(issues[4]['message'], 'Original criticism revised')
        self.assertTrue(review.is_ci_threshold_eligible(issues[2]))
        self.assertFalse(review.is_ci_threshold_eligible(issues[6]))
        self.assertTrue(review.is_ci_threshold_eligible(issues[7]))
        self.assertEqual(review.evaluate_ci(issues, [], 0, 0, 0)['medium_count'], 7)

    def test_stale_feedback_cannot_dismiss_changed_source(self):
        issue = finding('changed')
        record = feedback_record(issue, 'withdrawn', dismissed=True)
        issue['document_revision']['content_sha256'] = 'b' * 64
        self.attach([issue], {issue['issue_id']: record})
        self.assertTrue(issue['feedback_stale'])
        self.assertEqual(review.feedback_state(issue), 'needs_revalidation')
        self.assertTrue(review.is_ci_threshold_eligible(issue))
        self.assertTrue(issue['feedback_discussion'])

    def test_human_acceptance_keeps_withdrawn_finding_active(self):
        issue = finding('accepted')
        record = feedback_record(issue, 'withdrawn')
        record['human_resolution'] = 'accepted'
        self.attach([issue], {issue['issue_id']: record})
        self.assertEqual(review.feedback_state(issue), 'accepted')
        self.assertFalse(review.is_history_issue(issue))

    def test_cli_render_needs_no_key_and_uses_saved_ci_thresholds(self):
        issue = finding('cli')
        payload = {
            'metadata': {'report_run_at_display': 'Saved review date',
                         'report_time_zone': 'Europe/London', 'mode': 'per-page',
                         'filter_label': 'Saved review', 'model': 'saved-model',
                         'ai_review_policy_version': 'saved-policy', 'files_reviewed': 1},
            'issues': [issue], 'errors': [],
            'ci': {'thresholds': {'high': 0, 'medium': 0, 'api_errors': 0}},
        }
        source = self.root / 'saved.json'
        source.write_text(json.dumps(payload))
        self.attach([], {})
        env = {key: value for key, value in os.environ.items() if key != 'DEEPSEEK_API_KEY'}
        result = subprocess.run([
            sys.executable, str(Path(review.__file__).resolve()), 'render',
            '--report', str(source), '--feedback-file', str(self.feedback),
            '--report-dir', str(self.root / 'cli-output'), '--ci',
        ], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('No checks or AI calls were run', result.stdout)
        output = json.loads((self.root / 'cli-output' / 'ai-doc-review.json').read_text())
        self.assertEqual(output['ci']['thresholds']['medium'], 0)
        self.assertFalse(output['ci']['passed'])

    def test_render_preserves_snapshot_ids_and_shows_history_and_evidence(self):
        issues = [finding('revised'), finding('withdrawn'), finding('pending')]
        records = {issues[0]['issue_id']: feedback_record(issues[0], 'revised'),
                   issues[1]['issue_id']: feedback_record(issues[1], 'withdrawn'),
                   issues[2]['issue_id']: feedback_record(issues[2], pending=True)}
        self.attach([], records)
        metadata = {
            'report_run_at_display': '1 November 2026', 'report_time_zone': 'Europe/London',
            'mode': 'per-page', 'filter_label': 'Full review', 'model': 'saved-model',
            'ai_review_policy_version': 'saved-policy', 'files_reviewed': 1,
        }
        payload = {'metadata': metadata, 'issues': issues, 'errors': [],
                   'ci': {'thresholds': {'high': 0, 'medium': 0, 'api_errors': 0}}}
        source = self.root / 'saved.json'
        original = json.dumps(payload, indent=2).encode()
        source.write_bytes(original)
        output = self.root / 'rendered'
        with patch.object(review, 'request_review', side_effect=AssertionError('No AI allowed')), \
             patch.object(review, 'run_per_page_checks', side_effect=AssertionError('No checks allowed')), \
             patch.object(review, 'REPORT'), patch.object(review, 'JSON_REPORT'), \
             patch.object(review, 'MARKDOWN_REPORT'):
            ci = review.render_saved_report(source, self.feedback, output)
        self.assertFalse(ci['passed'])
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual((output / 'original-report.json').read_bytes(), original)
        rendered = json.loads((output / 'ai-doc-review.json').read_text())
        self.assertEqual(rendered['metadata']['report_run_at_display'], '1 November 2026')
        self.assertIn('feedback_updated_at', rendered['metadata'])
        self.assertEqual({i['issue_id'] for i in rendered['issues']}, {i['issue_id'] for i in issues})
        self.assertEqual(rendered['summary']['history'], 1)
        document = (output / 'ai-doc-review.html').read_text()
        active, history = document.split('<table id="historyTable">', 1)
        self.assertNotIn('data-issue-id="qa-withdrawn"', active)
        self.assertIn('data-issue-id="qa-withdrawn"', history)
        self.assertIn('Original criticism and suggestion', document)
        self.assertIn('Revised criticism', document)
        self.assertIn('Challenged — awaiting decision', document)
        self.assertIn('Source passage</blockquote>', document)
        self.assertIn('&lt;script&gt;unsafe()', document)
        self.assertNotIn('<script>unsafe()', document)
        markdown = (output / 'ai-doc-review.md').read_text()
        self.assertIn('## Withdrawn / dismissed', markdown)
        self.assertIn('**Original criticism:**', markdown)
        # Syntax check the generated script without a browser or external service.
        script = document.split('<script>', 1)[1].split('</script>', 1)[0]
        js = self.root / 'report.js'
        js.write_text(script)
        subprocess.run(['node', '--check', str(js)], check=True, capture_output=True)

    def test_render_refuses_overwriting_input_or_another_snapshot(self):
        source = self.root / 'ai-doc-review.json'
        source.write_text(json.dumps({'metadata': {}, 'issues': [], 'ci': {}, 'errors': []}))
        with self.assertRaisesRegex(ValueError, 'must not be overwritten'):
            review.render_saved_report(source, self.feedback, self.root)
        output = self.root / 'other'
        output.mkdir()
        (output / 'original-report.json').write_text('another snapshot')
        with self.assertRaisesRegex(ValueError, 'different original report'):
            review.render_saved_report(source, self.feedback, output)


if __name__ == '__main__':
    unittest.main()
