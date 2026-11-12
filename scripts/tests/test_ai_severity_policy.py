import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ai_docs_review as review


class AISeverityPolicyTests(unittest.TestCase):
    def test_reported_heading_error_is_low_consistency_improvement(self):
        heading = '### Cloud-Hosted integration testing {/* #cloud-hosted-integration-testing */}'
        issue = {
            'source': 'ai', 'severity': 'high', 'confidence': 'high',
            'type': 'defect', 'category': 'unfinished', 'line': 1,
            'original': heading,
            'message': "Inconsistent capitalisation within the heading. This is a minor consistency issue rather than a defect, but the heading reads awkwardly.",
            'suggestion': 'Use sentence case.',
        }
        result = review.normalise_ai_issue(issue, heading, 'example.md', review.GrammarReview.allowed_categories)
        self.assertEqual((result['severity'], result['type'], result['category']),
                         ('low', 'improvement', 'consistency'))
        self.assertEqual(result['model_reported_severity'], 'high')
        self.assertEqual(issue['severity'], 'high')

    def test_ai_high_is_capped_but_deterministic_high_is_preserved(self):
        ai = {'source': 'ai', 'severity': 'high', 'confidence': 'high', 'type': 'defect'}
        static = {**ai, 'source': 'vale'}
        ci = review.evaluate_ci([ai, static], [], 0, 0, 0)
        self.assertEqual(ai['severity'], 'medium')
        self.assertEqual(ai['model_reported_severity'], 'high')
        self.assertEqual(static['severity'], 'high')
        self.assertEqual((ci['high_count'], ci['medium_count']), (1, 1))

    def test_severity_cap_is_idempotent_for_saved_reports(self):
        issue = {'source': 'ai', 'severity': 'high'}
        review.apply_ai_severity_policy(issue)
        first = copy.deepcopy(issue)
        review.apply_ai_severity_policy(issue)
        self.assertEqual(issue, first)


if __name__ == '__main__':
    unittest.main()
