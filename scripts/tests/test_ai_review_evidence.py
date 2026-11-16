import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ai_docs_review as review


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.path = Path('docs/tools/example.md')
        self.content = 'First explanation.\nSecond explanation.'
        self.issue = dict(source='ai', severity='medium', confidence='high', type='defect',
                          category='consistency', line=1, original='First explanation.',
                          message='The passages conflict.', suggestion='Reconcile the explanations.',
                          reader_impact='Readers receive conflicting instructions.', rule_basis='Internal consistency',
                          evidence=[{'file': str(self.path), 'quote': q} for q in self.content.splitlines()])

    def test_comparison_requires_two_distinct_verified_passages(self):
        self.assertTrue(review.valid_review_evidence(self.issue, {str(self.path): self.content}))
        for evidence in [self.issue['evidence'][:1], self.issue['evidence'][:1] * 2,
                         [*self.issue['evidence'][:1], {'file': str(self.path), 'quote': 'Invented.'}],
                         [{'file': 'missing.md', 'quote': self.content}]]:
            with self.subTest(evidence=evidence):
                issue = dict(self.issue, evidence=evidence)
                self.assertFalse(review.valid_review_evidence(issue, {str(self.path): self.content}))

    def test_runtime_rejects_missing_reader_impact(self):
        issue = dict(self.issue, reader_impact='')
        self.assertIsNone(review.normalise_ai_issue(issue, self.content, str(self.path),
                          {'consistency'}, evidence_sources={str(self.path): self.content}))

    def test_verifier_rejects_bad_diagnosis_and_retains_supported_correction(self):
        # Represents the report's false comma-splice claim versus a supported conflict.
        proposals = [dict(self.issue, message='A coordinated verb is a comma splice.'), self.issue]
        response = {'assessments': [dict(index=0, supported=False, reason='No independent clause.'),
                                   dict(index=1, supported=True, reason='Instructions contradict.', medium_justified=True)]}
        with patch.object(review, 'request_review', return_value=response):
            result = review.verify_page_findings(proposals, self.path, self.content, 'unused')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['severity'], 'medium')
        self.assertEqual(proposals[0]['severity'], 'medium')

    def test_medium_requires_separate_justification(self):
        response = {'assessments': [dict(index=0, supported=True, reason='Minor navigation friction.')]}
        with patch.object(review, 'request_review', return_value=response):
            result = review.verify_page_findings([self.issue], self.path, self.content, 'unused')
        self.assertEqual(result[0]['severity'], 'low')

    def test_incomplete_or_duplicate_verification_is_an_error(self):
        entry = dict(index=0, supported=True, reason='Verified.')
        for response in [{'assessments': []}, {'assessments': [entry, entry]}, {'issues': []}]:
            with self.subTest(response=response), patch.object(review, 'request_review', return_value=response):
                with self.assertRaises(ValueError):
                    review.verify_page_findings([self.issue], self.path, self.content, 'unused')

    def test_overlap_keeps_both_feedback_identities(self):
        issues = [dict(self.issue, file=str(self.path), issue_id='qa-one'),
                  dict(self.issue, file=str(self.path), issue_id='qa-two', category='structure')]
        review.attach_related_findings(issues)
        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[0]['related_findings'], ['qa-two'])
        self.assertEqual(issues[1]['related_findings'], ['qa-one'])

    def test_page_check_verifies_after_source_validation(self):
        issue = dict(self.issue, category='grammar', evidence=self.issue['evidence'][:1])
        with patch.object(review, 'request_review', side_effect=[{'issues': [issue]},
                {'assessments': [dict(index=0, supported=False, reason='Valid coordinated verbs.')]}]) as request:
            self.assertEqual(review.GrammarReview().run_page(self.path, self.content, 'unused'), [])
        self.assertEqual(request.call_count, 2)


if __name__ == '__main__':
    unittest.main()
