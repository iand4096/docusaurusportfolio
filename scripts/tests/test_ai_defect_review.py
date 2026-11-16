import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ai_docs_review as review
import test_ai_review_evidence as evidence


class DefectReviewTests(unittest.TestCase):
    def setUp(self):
        fixture = evidence.EvidenceTests()
        fixture.setUp()
        self.issue = fixture.issue
        self.path = fixture.path
        self.content = fixture.content
        self.accept = dict(index=0, supported=True, reason='Instructions conflict.',
            substantive_defect=True, reasonable_reading='Both passages concern the same operation.',
            why_reading_fails='One requires verification before deletion; the other reverses the order.',
            consequence='Following the second instruction can delete the only working index.',
            failure_kind='contradiction', medium_justified=True)

    def verify(self, assessment, issue=None):
        with patch.object(review, 'request_review', return_value={'assessments': [assessment]}):
            return review.verify_page_findings([issue or self.issue], self.path,
                                              self.content, 'unused', True)

    def test_default_preserves_deterministic_checks_and_excludes_optional_checks(self):
        full = review.selected_checks('full')
        names = {check.name for check in full}
        self.assertFalse(names & {'PortfolioReview', 'RepetitionReview', 'DiagramReview'})
        self.assertTrue({'GrammarReview', 'StructureReview', 'SiteWideConsistencyReview'} <= names)
        expected = {check.name for check in review.build_checks() if check.source != 'ai'}
        self.assertTrue(expected <= names)
        self.assertTrue(all(check.defects_only for check in full if check.source == 'ai'))
        editorial = review.selected_checks('editorial')
        self.assertTrue({'PortfolioReview', 'RepetitionReview', 'DiagramReview'} <= {c.name for c in editorial})
        self.assertFalse(any(c.defects_only for c in editorial))

    def test_real_contradiction_survives(self):
        self.assertEqual(len(self.verify(self.accept)), 1)
        self.assertEqual(self.verify(self.accept)[0]['severity'], 'medium')

    def test_preference_disguised_as_supported_defect_is_rejected(self):
        result = self.verify(dict(self.accept, substantive_defect=False,
                                 reason='The original has a reasonable conventional reading.'))
        self.assertEqual(result, [])

    def test_missing_or_invented_failure_contract_is_a_check_error(self):
        for changes in [{'substantive_defect': 'yes'}, {'reasonable_reading': ''},
                        {'why_reading_fails': ''}, {'consequence': ''},
                        {'failure_kind': 'could be smoother'}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.verify(dict(self.accept, **changes))

    def test_ambiguity_requires_distinct_interpretations(self):
        answer = dict(self.accept, failure_kind='ambiguous_meaning')
        for meanings in [None, [], ['One meaning'], ['Same', 'Same']]:
            with self.subTest(meanings=meanings), self.assertRaises(ValueError):
                self.verify(dict(answer, interpretations=meanings))
        self.assertEqual(len(self.verify(dict(answer, interpretations=[
            'Delete the live index before verification.',
            'Delete the old copy after verification.']))), 1)

    def test_optional_findings_skip_verification_in_default_review(self):
        with patch.object(review, 'request_review') as request:
            result = review.verify_page_findings([dict(self.issue, type='improvement')],
                self.path, self.content, 'unused', True)
        self.assertEqual(result, [])
        request.assert_not_called()

    def test_withdrawn_claims_are_reasoning_examples_not_exemptions(self):
        self.assertIn('comma-delimited parenthetical', review.SUBSTANTIVE_DEFECT_RULES)
        self.assertIn('display label', review.SUBSTANTIVE_DEFECT_RULES)
        self.assertIn('not blanket exemptions', review.SUBSTANTIVE_DEFECT_RULES)

    def test_full_mode_applies_strict_prompt_and_verification_to_page_checks(self):
        check = next(c for c in review.selected_checks('full') if c.name == 'GrammarReview')
        with patch.object(review, 'request_review', side_effect=[{'issues': [self.issue]},
                {'assessments': [self.accept]}]) as request:
            result = check.run_page(self.path, self.content, 'unused')
        self.assertEqual(len(result), 1)
        self.assertIn('REVIEW INTENT: substantive defects only', request.call_args_list[0].args[0])
        self.assertIn('strongest reasonable', request.call_args_list[1].args[0])

    def test_review_intent_separates_cache_entries(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory, patch.object(review, 'PROJECT_ROOT', Path(directory)):
            full = next(c for c in review.selected_checks('full') if c.name == 'GrammarReview')
            editorial = next(c for c in review.selected_checks('editorial') if c.name == 'GrammarReview')
            compute = unittest.mock.Mock(return_value=[])
            for check in [full, editorial, full, editorial]:
                review.cached_ai_check(check, {'example.md': self.content}, 'per-page', compute)
            self.assertEqual(compute.call_count, 2)


if __name__ == '__main__':
    unittest.main()
