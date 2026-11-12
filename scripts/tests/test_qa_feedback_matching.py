import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ai_docs_review as review
import qa_feedback as feedback
from test_qa_report_feedback import finding, feedback_record


class FeedbackMatchingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='qa-matching-')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'feedback.json'
        self.old = finding('old')
        self.record = feedback_record(self.old, 'withdrawn', dismissed=True)

    def attach(self, issue, records=None):
        self.path.write_text(json.dumps({'schema_version': 1, 'records':
                                        records if records is not None else {'qa-old': self.record}}))
        feedback.attach_feedback_status([issue], self.path)
        return issue

    def test_same_bytes_new_commit_carries_resolution_and_has_new_occurrence(self):
        previous = self.attach(copy.deepcopy(self.old))
        current = copy.deepcopy(self.old)
        current['document_revision']['git_commit'] = 'b' * 40
        current['issue_id'] = 'qa-new-report-reference'
        self.attach(current)
        self.assertEqual(current['persistent_issue_id'], previous['persistent_issue_id'])
        self.assertNotEqual(current['occurrence_id'], previous['occurrence_id'])
        self.assertEqual(current['human_resolution'], 'dismissed')
        self.assertEqual(current['issue_id'], 'qa-new-report-reference')

    def test_changed_document_or_moved_passage_links_history_without_dismissal(self):
        previous = self.attach(copy.deepcopy(self.old))
        current = copy.deepcopy(self.old)
        current['document_revision']['content_sha256'] = 'b' * 64
        current['line'] = 80
        self.attach(current)
        self.assertEqual(current['persistent_issue_id'], previous['persistent_issue_id'])
        self.assertEqual(current['feedback_match'], 'exact')
        self.assertEqual(review.feedback_state(current), 'needs_revalidation')
        self.assertTrue(current['feedback_discussion'])
        self.assertIsNone(current['human_resolution'])
        self.assertIsNone(current['effective_ai_decision'])
        self.assertTrue(review.is_ci_threshold_eligible(current))

    def test_only_case_and_whitespace_variations_match(self):
        current = copy.deepcopy(self.old)
        current['message'] = '  ORIGINAL   criticism\nold '
        current['original'] = 'source   passage'
        self.attach(current)
        self.assertEqual(current['feedback_match'], 'exact')

    def test_reworded_claim_edited_passage_and_renamed_file_do_not_match(self):
        for field, value in [('message', 'Semantically similar, differently phrased criticism'),
                             ('original', 'Edited source passage'), ('file', 'renamed.md')]:
            with self.subTest(field=field):
                current = copy.deepcopy(self.old)
                current[field] = value
                self.attach(current)
                self.assertEqual(current['feedback_match'], 'none')
                self.assertIsNone(current['human_resolution'])
                self.assertFalse(review.is_history_issue(current))

    def test_changed_suggestion_requires_revalidation_even_if_source_is_unchanged(self):
        current = copy.deepcopy(self.old)
        current['suggestion'] = 'A materially different proposed fix'
        self.attach(current)
        self.assertEqual(current['feedback_revalidation_reason'], 'suggestion_changed')
        self.assertIsNone(current['human_resolution'])

    def test_duplicate_records_are_ambiguous_and_not_suppressed(self):
        current = self.attach(copy.deepcopy(self.old), {
            'qa-old': self.record, 'qa-duplicate': copy.deepcopy(self.record)})
        self.assertEqual(current['feedback_match'], 'ambiguous')
        self.assertIsNone(current['human_resolution'])
        self.assertTrue(review.is_ci_threshold_eligible(current))

    def test_revalidate_new_occurrence_without_ai_and_keep_legacy_history(self):
        previous = self.attach(copy.deepcopy(self.old))
        current = copy.deepcopy(self.old)
        current['issue_id'] = 'qa-current'
        current['document_revision']['content_sha256'] = hashlib.sha256(b'Source passage\nNew context').hexdigest()
        report = Path(self.temp.name) / 'report.json'
        report.write_text(json.dumps({'issues': [current]}))
        with patch.object(feedback, '_source_for_report_finding', return_value='Source passage\nNew context'), \
             patch.object(review, 'request_review', side_effect=AssertionError('No AI allowed')):
            feedback.resolve('qa-current', 'dismissed', 'Reviewed changed context; earlier reasoning still applies.',
                             feedback_path=self.path, report=report)
        # Loading the new report finds the original persistent record.
        feedback.attach_feedback_status([current], self.path)
        self.assertEqual(current['persistent_issue_id'], previous['persistent_issue_id'])
        self.assertEqual(current['human_resolution'], 'dismissed')
        self.assertFalse(current['feedback_needs_revalidation'])
        self.assertIsNone(current['effective_ai_decision'])
        saved = json.loads(self.path.read_text())['records']['qa-old']
        self.assertEqual(len(saved['adjudications']), 1)
        self.assertEqual(saved['occurrences'][0]['issue_id'], 'qa-current')
        # Historical report still links, but cannot inherit the new revision's resolution.
        old = copy.deepcopy(self.old)
        feedback.attach_feedback_status([old], self.path)
        self.assertTrue(old['feedback_needs_revalidation'])

    def test_challenge_new_occurrence_persists_identity_and_drops_old_dismissal(self):
        previous = self.attach(copy.deepcopy(self.old))
        current = copy.deepcopy(self.old)
        current['issue_id'] = 'qa-new-occurrence'
        current['document_revision']['content_sha256'] = 'b' * 64
        report = Path(self.temp.name) / 'report.json'
        report.write_text(json.dumps({'issues': [current]}))
        answer = {'decision': 'upheld', 'reason': 'A fresh decision for the new source.',
                  'evidence': ['Source passage'], 'revised_message': None,
                  'revised_suggestion': None}
        with patch.object(feedback, '_source_for_report_finding', return_value='Source passage\nNew context'):
            feedback.challenge('qa-new-occurrence', 'Review this source version.', report=report,
                               feedback_path=self.path, api_key='not-used',
                               request_review=lambda *_: answer)
        feedback.attach_feedback_status([current], self.path)
        self.assertEqual(current['persistent_issue_id'], previous['persistent_issue_id'])
        self.assertEqual(current['effective_ai_decision'], 'upheld')
        self.assertIsNone(current['human_resolution'])
        saved = json.loads(self.path.read_text())['records']
        self.assertEqual(list(saved), ['qa-old'])
        self.assertEqual(saved['qa-old']['occurrences'][0]['issue_id'], 'qa-new-occurrence')


if __name__ == '__main__':
    unittest.main()
