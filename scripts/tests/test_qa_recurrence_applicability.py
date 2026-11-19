import copy
import hashlib
import json
import sys
import tempfile
import unittest
import subprocess
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import qa_feedback as feedback
import qa_recurrence as recurrence
import qa_embeddings as embeddings
from test_qa_report_feedback import finding, feedback_record


class CachedIndex:
    def populate(self, issues):
        pass

    def similarity(self, left, right):
        return None


class ApplicabilityTests(unittest.TestCase):
    def setUp(self):
        (Path(__file__).resolve().parents[2] / '.qa').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='qa-applicability-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.registry, self.cache, self.report = [self.root / n for n in ('feedback.json', 'cache.json', 'report.json')]
        self.old_source = 'Source passage\nThe pilot lacked incremental previews.\n'
        self.new_source = self.old_source + '\nUnrelated footer edit.\n'
        self.old = finding('old')
        self.old['document_revision'] = self.revision(self.old_source)
        self.record = feedback_record(self.old, 'withdrawn')
        feedback.preserve_precedent(self.record, self.old, rebuttal='The limitation is already stated.',
                                   adjudication=self.record['adjudications'][-1],
                                   resolution={'decision': 'dismissed', 'reason': 'Reviewed the evidence.'})
        self.new = copy.deepcopy(self.old)
        self.new.update(issue_id='qa-new', message='The same allegation paraphrased.')
        self.new['document_revision'] = self.revision(self.new_source)
        self.answer = {'complaint_relationship': 'equivalent', 'prior_decision_applicability': 'applicable',
                       'document_change_impact': 'not_material', 'reason': 'The quoted rebuttal evidence is unchanged.',
                       'old_evidence': ['The pilot lacked incremental previews.'],
                       'new_evidence': ['The pilot lacked incremental previews.']}
        self.store = {'schema_version': 1, 'records': {'qa-old': self.record}}
        self.registry.write_text(json.dumps(self.store))

    @staticmethod
    def revision(source):
        return {'git_commit': 'a' * 40, 'content_sha256': hashlib.sha256(source.encode()).hexdigest(),
                'source_snapshot': source}

    def compare(self, answer=None):
        errors = recurrence.compare_recurrences([self.new], feedback_path=self.registry,
            cache_path=self.cache, api_key='unused', request_review=lambda *_: answer or self.answer,
            index=CachedIndex())
        self.report.write_text(json.dumps({'issues': [self.new]}))
        return errors

    def reuse(self):
        return recurrence.reuse_decision('qa-new', 'qa-old', 'I checked both source versions.',
            report=self.report, proposal=self.new['recurrence_candidates'][0]['proposal_id'],
            feedback_path=self.registry)

    def test_unrelated_edit_requires_explicit_approval_then_can_reuse(self):
        before = copy.deepcopy(self.record)
        self.assertEqual(self.compare(), [])
        feedback.attach_feedback_status([self.new], self.registry)
        self.assertIsNone(self.new['human_resolution'])
        self.assertTrue(recurrence.reusable(self.new['recurrence_candidates'][0]))
        self.report.write_text(json.dumps({'issues': [self.new]}))
        self.reuse()
        feedback.attach_feedback_status([self.new], self.registry)
        self.assertEqual(self.new['human_resolution'], 'dismissed')
        self.assertEqual(self.new['effective_ai_decision'], 'withdrawn')
        self.assertEqual(feedback.feedback_records(self.registry)['records']['qa-old'], before)

    def test_exact_claim_changed_source_takes_revalidation_route(self):
        self.new['message'] = self.old['message']
        self.assertEqual(self.compare(), [])
        self.assertTrue(self.new['recurrence_candidates'][0]['requires_revalidation'])
        feedback.attach_feedback_status([self.new], self.registry)
        self.assertTrue(self.new['feedback_needs_revalidation'])
        self.report.write_text(json.dumps({'issues': [self.new]}))
        precedent = copy.deepcopy(self.record['precedents'][0])
        self.reuse()
        saved = feedback.feedback_records(self.registry)['records']['qa-old']
        self.assertEqual(saved['precedents'][0], precedent)
        feedback.attach_feedback_status([self.new], self.registry)
        self.assertFalse(self.new['feedback_needs_revalidation'])
        self.assertEqual(self.new['human_resolution'], 'dismissed')

    def test_removed_rebuttal_evidence_makes_prior_decision_inapplicable(self):
        self.new['document_revision'] = self.revision('Source passage\nEvidence removed.\n')
        answer = {**self.answer, 'document_change_impact': 'material',
                  'new_evidence': ['Evidence removed.']}
        self.assertEqual(self.compare(answer), [])
        self.assertFalse(recurrence.reusable(self.new['recurrence_candidates'][0]))
        with self.assertRaisesRegex(ValueError, 'not safely reusable'):
            self.reuse()

    def test_same_quotation_different_defect_or_new_requirement_cannot_reuse(self):
        for relation in ('different', 'narrower', 'broader', 'uncertain'):
            with self.subTest(relation=relation):
                cache = self.root / f'{relation}.json'
                with patch.object(recurrence, 'DEFAULT_CACHE', cache):
                    self.cache = cache
                    self.assertEqual(self.compare({**self.answer, 'complaint_relationship': relation}), [])
                self.assertFalse(recurrence.reusable(self.new['recurrence_candidates'][0]))

    def test_legacy_decision_is_not_reusable_even_if_model_claims_applicable(self):
        self.record.pop('precedents')
        self.registry.write_text(json.dumps(self.store))
        self.assertEqual(self.compare(), [])
        self.assertEqual(self.new['recurrence_candidates'][0]['comparison']['prior_decision_applicability'], 'uncertain')

    def test_conflicting_prior_adjudications_require_human_resolution(self):
        opposite = copy.deepcopy(self.record['adjudications'][0])
        opposite['decision'] = 'upheld'
        feedback.preserve_precedent(self.record, self.old, adjudication=opposite)
        self.registry.write_text(json.dumps(self.store))
        self.assertEqual(self.compare(), [])
        candidate = self.new['recurrence_candidates'][0]
        self.assertTrue(candidate['comparison']['human_review_required'])
        with self.assertRaisesRegex(ValueError, 'not safely reusable'):
            self.reuse()

    def test_changed_history_invalidates_human_approval_token(self):
        self.assertEqual(self.compare(), [])
        store = feedback.feedback_records(self.registry)
        store['records']['qa-old']['discussion'].append({'role': 'human', 'text': 'New material evidence'})
        self.registry.write_text(json.dumps(store))
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.reuse()

    def test_later_rejection_or_new_feedback_invalidates_reuse(self):
        self.assertEqual(self.compare(), [])
        store = feedback.feedback_records(self.registry)
        store.setdefault('link_events', []).append({'decision': 'rejected',
            'pair_id': self.new['recurrence_candidates'][0]['proposal_id']})
        self.registry.write_text(json.dumps(store))
        with self.assertRaisesRegex(ValueError, 'registry changed'):
            self.reuse()

    def test_snapshot_restores_uncommitted_bytes_and_detects_tampering(self):
        self.assertEqual(feedback._source_for_report_finding(self.old, historical=True), self.old_source)
        broken = copy.deepcopy(self.old)
        broken['document_revision']['source_snapshot'] = 'Tampered'
        with self.assertRaisesRegex(ValueError, 'snapshot'):
            feedback._source_for_report_finding(broken, historical=True)

    def test_snapshot_does_not_override_current_source_check_for_challenge(self):
        with self.assertRaises(ValueError):
            feedback._source_for_report_finding(self.old, historical=False)

    def test_precedent_is_immutable_and_content_addressed(self):
        original = copy.deepcopy(self.record['precedents'][0])
        self.old['message'] = 'Changed after adjudication'
        self.assertEqual(self.record['precedents'][0], original)
        self.record['precedents'][0]['adjudication']['reason'] = 'Tampered'
        with self.assertRaisesRegex(ValueError, 'hash'):
            recurrence.previous_finding(self.record)

    def test_same_quotation_wrong_complaint_does_not_displace_semantic_match(self):
        other = copy.deepcopy(self.record)
        other.pop('precedents')
        other['latest_finding']['message'] = 'A completely different problem.'
        self.store['records']['qa-other'] = other
        class Index(CachedIndex):
            def similarity(index, left, right):
                return 0.1 if right['message'] == 'A completely different problem.' else 0.9
        self.new['original'] = 'A rewritten sentence with different words'
        ranked = recurrence.candidates(self.new, self.store, index=Index())
        self.assertEqual(ranked[0][1], 'qa-old')

    def test_embedding_cache_cannot_load_a_model_during_render(self):
        index = embeddings.ComplaintIndex(cache_path=self.root / 'vectors.json')
        with patch.dict(sys.modules, {'sentence_transformers': None}):
            self.assertIsNone(index.similarity(self.old, self.new))

    def test_retrieval_failure_is_visible_and_not_classified_as_clear(self):
        class BrokenIndex(CachedIndex):
            def populate(self, issues):
                raise RuntimeError('Model unavailable')
        errors = recurrence.compare_recurrences([self.new], feedback_path=self.registry,
            cache_path=self.cache, api_key='unused', request_review=lambda *_: self.answer,
            index=BrokenIndex())
        self.assertIn('Embedding retrieval unavailable', errors[0]['error'])
        self.assertTrue(self.new['recurrence_comparison_errors'])
        from qa_reporting import html_report
        self.assertFalse(html_report.ai_without_recurrence_concerns(self.new))

    def test_semantic_only_saved_proposal_survives_missing_vector_cache(self):
        self.new['original'] = 'An entirely rewritten quotation.'
        self.new['document_revision'] = self.revision(self.new_source.replace('Source passage', self.new['original']))
        class Index(CachedIndex):
            def similarity(index, left, right):
                return 0.9
        self.assertEqual(recurrence.compare_recurrences([self.new], feedback_path=self.registry,
            cache_path=self.cache, api_key='unused', request_review=lambda *_: self.answer,
            index=Index()), [])
        self.assertEqual(len(self.new['recurrence_candidates']), 1)
        recurrence.attach_candidates([self.new], self.registry, self.cache, index=CachedIndex())
        self.assertEqual(len(self.new['recurrence_candidates']), 1)
        self.assertEqual(self.new['recurrence_candidates'][0]['comparison']['complaint_relationship'], 'equivalent')

    def test_reuse_cli_verifies_snapshots_without_provider_key(self):
        self.assertEqual(self.compare(), [])
        import os
        env = {key: value for key, value in os.environ.items() if key != 'DEEPSEEK_API_KEY'}
        result = subprocess.run([sys.executable, 'scripts/ai_docs_review.py', 'reuse',
            '--report', str(self.report), '--issue', 'qa-new', '--previous', 'qa-old',
            '--proposal', self.new['recurrence_candidates'][0]['proposal_id'],
            '--reason', 'I checked the source and decision.', '--feedback-file', str(self.registry)],
            capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Human-approved decision reuse', result.stdout)

    def test_saved_report_exposes_applicability_precedent_and_reuse_command(self):
        self.assertEqual(self.compare(), [])
        import ai_docs_review as review
        payload = {'issues': [self.new], 'errors': [], 'metadata': {
            'report_run_at_display': '16 November 2026', 'report_time_zone': 'Europe/London',
            'mode': 'per-page', 'filter_label': 'Full review', 'model': 'test',
            'ai_review_policy_version': 'test', 'files_reviewed': 1},
            'ci': {'thresholds': {'high': 0, 'medium': 5, 'api_errors': 0}}}
        self.report.write_text(json.dumps(payload))
        before = self.registry.read_bytes()
        with patch.object(embeddings.ComplaintIndex, 'populate', side_effect=AssertionError('No model loading')):
            output = self.root / 'rendered'
            review.render_saved_report(self.report, self.registry, output)
        html = (output / 'ai-doc-review.html').read_text()
        markdown = (output / 'ai-doc-review.md').read_text()
        for text in ['Prior decision applicability', 'Document change impact',
                     'Exact decision precedent', 'Copy revalidate and reuse command']:
            self.assertIn(text, html)
        self.assertIn('**Prior Decision Applicability:** applicable', markdown)
        self.assertIn('ai_docs_review.py reuse', markdown)
        self.assertEqual(before, self.registry.read_bytes())

    def test_working_tree_snapshot_remains_available_after_file_changes(self):
        import ai_docs_review as review
        with tempfile.TemporaryDirectory(dir=review.PROJECT_ROOT / '.qa') as directory:
            source = Path(directory) / 'uncommitted.md'
            raw = b'Source passage\r\nUncommitted text.\r\n'
            source.write_bytes(raw)
            relative = source.relative_to(review.PROJECT_ROOT).as_posix()
            revision = feedback.git_document_revision(relative)
            self.assertEqual(revision['source_snapshot'].encode(), raw)
            source.write_text('Different working tree bytes')
            issue = {**self.old, 'file': relative, 'document_revision': revision}
            self.assertEqual(feedback._source_for_report_finding(issue, historical=True).encode(), raw)
            with self.assertRaisesRegex(ValueError, 'changed'):
                feedback._source_for_report_finding(issue, historical=False)

    def test_applicable_requires_actual_source_evidence_and_valid_enums(self):
        precedent = self.record['precedents'][0]
        for change in [{'document_change_impact': 'unchanged'},
                       {'complaint_relationship': 'same'},
                       {'old_evidence': ['Original criticism old']}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                recurrence.validate_comparison({**self.answer, **change}, self.old, self.new,
                                              self.old_source, self.new_source, precedent)

    def test_ai_withdrawal_without_human_dismissal_never_removes_ci_eligibility(self):
        self.record['precedents'] = []
        feedback.preserve_precedent(self.record, self.old, rebuttal='Evidence is present.',
                                   adjudication=self.record['adjudications'][0])
        self.registry.write_text(json.dumps(self.store))
        self.assertEqual(self.compare(), [])
        self.reuse()
        feedback.attach_feedback_status([self.new], self.registry)
        self.assertEqual(self.new['effective_ai_decision'], 'withdrawn')
        self.assertIsNone(self.new['human_resolution'])
        from qa_policy import is_ci_threshold_eligible
        self.assertTrue(is_ci_threshold_eligible(self.new))


if __name__ == '__main__':
    unittest.main()
