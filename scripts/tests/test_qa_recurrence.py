import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ai_docs_review as review
import qa_feedback as feedback
import qa_recurrence as recurrence
from test_qa_report_feedback import finding, feedback_record


class RecurrenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='qa-recurrence-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.registry = self.root / 'feedback.json'
        self.cache = self.root / 'cache.json'
        self.report = self.root / 'report.json'
        self.source = 'Source passage\nFull surrounding context\n'
        self.old = finding('old')
        self.old['document_revision']['content_sha256'] = hashlib.sha256(self.source.encode()).hexdigest()
        self.old['message'] = 'The sentence has no subject.'
        self.record = feedback_record(self.old, 'withdrawn', dismissed=True)
        self.new = copy.deepcopy(self.old)
        self.new.update(issue_id='qa-new', category='grammar', message='A subject is missing from this sentence.')
        self.store = {'schema_version': 1, 'records': {'qa-old': self.record}}
        self.registry.write_text(json.dumps(self.store))
        self.answer = {'verdict': 'same_complaint', 'reason': 'Both allege an absent subject.',
                       'old_evidence': ['The sentence has no subject.'],
                       'new_evidence': ['A subject is missing from this sentence.']}

    def attach(self):
        feedback.attach_feedback_status([self.new], self.registry)
        recurrence.attach_candidates([self.new], self.registry, self.cache)
        self.report.write_text(json.dumps({'issues': [self.new]}))

    def decide(self, decision='confirmed'):
        self.attach()
        with patch.object(feedback, '_source_for_report_finding', return_value=self.source):
            return recurrence.decide_link('qa-new', 'qa-old', decision, 'I compared the allegations.',
                report=self.report, feedback_path=self.registry)

    def test_rewording_and_category_changes_propose_without_resolving(self):
        self.attach()
        self.assertEqual(self.new['feedback_match'], 'none')
        self.assertEqual(self.new['recurrence_candidates'][0]['record_id'], 'qa-old')
        self.assertIsNone(self.new['human_resolution'])
        self.assertIsNone(self.new['effective_ai_decision'])
        self.assertFalse(review.is_history_issue(self.new))

    def test_candidates_use_passage_overlap_not_category_and_exclude_other_files(self):
        self.new['original'] = 'Source passages'
        self.assertTrue(recurrence.candidates(self.new, self.store))
        self.new['file'] = 'unrelated.md'
        self.assertFalse(recurrence.candidates(self.new, self.store))
        self.new['file'] = self.old['file']
        self.new['original'] = 'Entirely different quotation'
        self.assertFalse(recurrence.candidates(self.new, self.store))

    def test_ai_comparison_is_cached_without_modifying_feedback(self):
        before = self.registry.read_bytes()
        request = Mock(return_value=self.answer)
        with patch.object(feedback, '_source_for_report_finding', return_value=self.source):
            for _ in range(2):
                failures = recurrence.compare_recurrences([self.new], feedback_path=self.registry,
                    cache_path=self.cache, api_key='unused', request_review=request)
                self.assertEqual(failures, [])
        self.assertEqual(request.call_count, 1)
        self.assertEqual(self.registry.read_bytes(), before)
        self.assertEqual(self.new['recurrence_candidates'][0]['comparison']['verdict'], 'same_complaint')
        self.attach()
        self.assertIsNone(self.new['effective_ai_decision'])
        self.assertIsNone(self.new['human_resolution'])

    def test_changed_source_suggestion_or_rebuttal_invalidates_comparison_cache(self):
        baseline = recurrence.comparison_id(self.new, 'qa-old', self.record)
        for field in ('suggestion', 'message', 'document_revision'):
            changed = copy.deepcopy(self.new)
            changed[field] = {'content_sha256': 'b' * 64} if field == 'document_revision' else 'Changed'
            self.assertNotEqual(baseline, recurrence.comparison_id(changed, 'qa-old', self.record))
        record = copy.deepcopy(self.record)
        record['discussion'].append({'role': 'human', 'text': 'New evidence'})
        self.assertNotEqual(baseline, recurrence.comparison_id(self.new, 'qa-old', record))

    def test_invalid_evidence_network_error_or_missing_key_leaves_unresolved(self):
        invalid = {**self.answer, 'new_evidence': ['Invented quotation']}
        for key, request in [('unused', Mock(return_value=invalid)),
                             ('unused', Mock(side_effect=RuntimeError('API unavailable'))),
                             (None, Mock())]:
            with self.subTest(key=key, request=request):
                with patch.object(feedback, '_source_for_report_finding', return_value=self.source):
                    failures = recurrence.compare_recurrences([self.new], feedback_path=self.registry,
                        cache_path=self.cache, api_key=key, request_review=request)
                self.assertEqual(len(failures), 1)
                self.assertIsNone(self.new['recurrence_candidates'][0]['comparison'])
                self.assertFalse(self.cache.exists())
        self.attach()
        self.assertFalse(review.is_history_issue(self.new))

    def test_different_or_uncertain_verdict_does_not_link(self):
        for verdict in ('different_complaint', 'uncertain'):
            with self.subTest(verdict=verdict), patch.object(feedback, '_source_for_report_finding', return_value=self.source):
                answer = {**self.answer, 'verdict': verdict}
                recurrence.compare_recurrences([self.new], feedback_path=self.registry,
                    cache_path=self.root / (verdict + '.json'), api_key='unused', request_review=lambda *_: answer)
                self.assertEqual(self.new['recurrence_candidates'][0]['comparison']['verdict'], verdict)
                self.assertEqual(feedback.match_feedback(self.new, self.store['records'])[2], 'none')

    def test_confirmation_preserves_old_record_but_never_inherits_dismissal(self):
        before = copy.deepcopy(self.record)
        self.decide()
        self.attach()
        saved = feedback.feedback_records(self.registry)
        self.assertEqual(saved['records']['qa-old'], before)
        self.assertEqual(len(saved['link_events']), 1)
        self.assertEqual(self.new['persistent_issue_id'], feedback.persistent_id('qa-old', self.record))
        self.assertEqual(self.new['feedback_match'], 'exact')
        self.assertIsNone(self.new['human_resolution'])
        self.assertIsNone(self.new['effective_ai_decision'])
        self.assertFalse(review.is_history_issue(self.new))
        self.assertIn('awaiting human resolution', review.feedback_label(self.new))
        with patch.object(feedback, '_source_for_report_finding', return_value=self.source):
            feedback.resolve('qa-new', 'dismissed', 'I checked the prior rebuttal applies.',
                             report=self.report, feedback_path=self.registry)
        self.attach()
        self.assertTrue(review.is_history_issue(self.new))
        self.assertEqual(feedback.feedback_records(self.registry)['records']['qa-old'], before)
        self.new['document_revision']['content_sha256'] = 'b' * 64
        self.attach()
        self.assertTrue(self.new['feedback_needs_revalidation'])
        self.assertIsNone(self.new['human_resolution'])

    def test_rejection_suppresses_only_the_reviewed_pair(self):
        self.decide('rejected')
        self.attach()
        self.assertEqual(self.new['recurrence_candidates'], [])
        self.assertEqual(len(feedback.feedback_records(self.registry)['records']), 1)
        self.new['suggestion'] = 'New proposed fix'
        self.attach()
        self.assertEqual(len(self.new['recurrence_candidates']), 1)

    def test_stale_previous_record_and_bad_sources_cannot_be_linked(self):
        self.attach()
        store = feedback.feedback_records(self.registry)
        store['records']['qa-old']['latest_finding']['message'] = 'A changed complaint'
        self.registry.write_text(json.dumps(store))
        with patch.object(feedback, '_source_for_report_finding', return_value=self.source):
            with self.assertRaisesRegex(ValueError, 'current proposal'):
                recurrence.decide_link('qa-new', 'qa-old', 'confirmed', 'Reviewed',
                    report=self.report, feedback_path=self.registry)
        with patch.object(feedback, '_source_for_report_finding', return_value='Missing original quotation'):
            with self.assertRaisesRegex(ValueError, 'quotation'):
                recurrence.decide_link('qa-new', 'qa-old', 'confirmed', 'Reviewed',
                    report=self.report, feedback_path=self.registry)

    def test_report_exports_evidence_and_shell_safe_confirmation_commands(self):
        self.new['message'] += ' <script>bad()</script>'
        self.attach()
        html = review.recurrence_html(self.new, '/tmp/report with spaces.json')
        self.assertIn('Previous allegation', html)
        self.assertIn('Previous rebuttal', html)
        self.assertIn('Copy confirm link command', html)
        self.assertIn('--decision rejected', html)
        self.assertIn('&lt;script&gt;bad()', html)
        self.assertNotIn('<script>bad()', html)
        command = review.recurrence_command('link', '/tmp/a $(echo secret).json',
            issue='qa-new', previous='qa-old', decision='confirmed', reason='Human reason')
        import shlex
        args = shlex.split(command)
        self.assertEqual(args[args.index('--report') + 1], '/tmp/a $(echo secret).json')

    def test_link_token_works_with_original_report_without_embedded_candidates(self):
        self.attach()
        token = self.new['recurrence_candidates'][0]['proposal_id']
        original = copy.deepcopy(self.new)
        original.pop('recurrence_candidates')
        self.report.write_text(json.dumps({'issues': [original]}))
        with patch.object(feedback, '_source_for_report_finding', return_value=self.source):
            recurrence.decide_link('qa-new', 'qa-old', 'confirmed', 'Same allegation',
                report=self.report, proposal=token, feedback_path=self.registry)
        self.attach()
        self.assertIsNotNone(self.new['feedback_link_confirmation'])
        self.assertIsNone(self.new['human_resolution'])

    def test_render_retains_embedded_comparison_without_local_cache(self):
        with patch.object(feedback, '_source_for_report_finding', return_value=self.source):
            recurrence.compare_recurrences([self.new], feedback_path=self.registry,
                cache_path=self.cache, api_key='unused', request_review=lambda *_: self.answer)
        self.cache.unlink()
        recurrence.attach_candidates([self.new], self.registry, self.cache)
        self.assertEqual(self.new['recurrence_candidates'][0]['comparison']['verdict'], 'same_complaint')

    def test_invalid_schema_and_corrupt_cache_do_not_resolve_or_break_render(self):
        self.cache.write_text('broken JSON')
        recurrence.attach_candidates([self.new], self.registry, self.cache)
        self.assertEqual(len(self.new['recurrence_candidates']), 1)
        with patch.object(feedback, '_source_for_report_finding', return_value=self.source):
            failures = recurrence.compare_recurrences([self.new], feedback_path=self.registry,
                cache_path=self.cache, api_key='unused', request_review=lambda *_: {'verdict': 'withdrawn'})
        self.assertTrue(failures)
        self.assertIsNone(self.new['recurrence_candidates'][0]['comparison'])

    def test_saved_report_render_exports_comparison_without_network_or_feedback_writes(self):
        with patch.object(feedback, '_source_for_report_finding', return_value=self.source):
            recurrence.compare_recurrences([self.new], feedback_path=self.registry,
                cache_path=self.cache, api_key='unused', request_review=lambda *_: self.answer)
        payload = {'issues': [self.new], 'errors': [], 'metadata': {
            'report_run_at_display': '13 November 2026', 'report_time_zone': 'Europe/London',
            'mode': 'per-page', 'filter_label': 'Full review', 'model': 'test-model',
            'ai_review_policy_version': 'test-policy', 'files_reviewed': 1},
            'ci': {'thresholds': {'high': 0, 'medium': 5, 'api_errors': 0}}}
        self.report.write_text(json.dumps(payload))
        before = self.registry.read_bytes()
        output = self.root / 'rendered'
        with patch.object(review, 'request_review', side_effect=AssertionError('No network')), \
             patch.object(review, 'REPORT'), patch.object(review, 'JSON_REPORT'), \
             patch.object(review, 'MARKDOWN_REPORT'):
            review.render_saved_report(self.report, self.registry, output)
        self.assertEqual(self.registry.read_bytes(), before)
        html = (output / 'ai-doc-review.html').read_text()
        markdown = (output / 'ai-doc-review.md').read_text()
        exported = json.loads((output / 'ai-doc-review.json').read_text())
        self.assertIn('Challenge links (1 possible · 0 confirmed)', html)
        self.assertIn('id="feedbackFilter"', html)
        self.assertIn('class="review-recurrence"', html)
        self.assertIn('data-recurrence="possible"', html)
        self.assertIn('AI comparison: same complaint', html)
        self.assertIn('**AI comparison:** same_complaint', markdown)
        self.assertIn('--proposal ', markdown)
        self.assertIn(str(self.registry), markdown)
        self.assertEqual(exported['issues'][0]['recurrence_candidates'][0]['comparison']['verdict'], 'same_complaint')
        js = self.root / 'report.js'
        js.write_text(html.split('<script>', 1)[1].split('</script>', 1)[0])
        subprocess.run(['node', '--check', str(js)], check=True, capture_output=True)
        # Exercise the generated filtering and jump actions against a minimal DOM.
        filter_script = self.root / 'filters.js'
        code = js.read_text()
        filter_script.write_text(code[code.index('    function applyFilters() {'):code.index('    // Keep copied recurrence commands')])
        harness = self.root / 'filter-test.js'
        harness.write_text(r'''
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const element = () => ({value:'', handlers:{}, addEventListener(name, fn) {this.handlers[name] = fn;}, scrollIntoView() {this.scrolled = true;}});
const severityFilter = element(), sourceFilter = element(), feedbackFilter = element();
const ids = Object.fromEntries(['findingFilterStatus','showPossibleLinks','showAllFindings','showAIWithoutRecurrence','activeFindingsTitle'].map(id => [id,element()]));
const details = {open:false}, history = {open:false};
const rows = [
    {dataset:{severity:'low', source:'ai', recurrence:'possible', aiClear:'true'}, style:{}},
    {dataset:{severity:'medium', source:'ai', recurrence:'confirmed'}, style:{}},
    {dataset:{severity:'low', source:'vale', recurrence:''}, style:{}}
];
rows[0].querySelector = () => details;
rows[0].closest = () => history;
ids['finding-1'] = rows[0];
const link = element(); link.getAttribute = () => '#finding-1';
const document = {
    getElementById: id => ids[id],
    querySelectorAll: selector => selector === 'tr[data-severity]' ? rows : [link]
};
vm.runInNewContext(fs.readFileSync(process.argv[2],'utf8'), {document,severityFilter,sourceFilter,feedbackFilter});
assert.equal(ids.findingFilterStatus.textContent, '3 of 3 findings shown.');
ids.showPossibleLinks.handlers.click();
assert.equal(feedbackFilter.value, 'possible');
assert.equal(rows[0].style.display, ''); assert.equal(rows[1].style.display, 'none');
assert.equal(rows[2].style.display, 'none');
assert.equal(ids.activeFindingsTitle.scrolled, true);
sourceFilter.value = 'vale'; sourceFilter.handlers.change();
assert.match(ids.findingFilterStatus.textContent, /No findings match/);
ids.showAllFindings.handlers.click();
assert.equal(sourceFilter.value, '');
feedbackFilter.value = 'confirmed'; feedbackFilter.handlers.change();
assert.equal(rows[0].style.display, 'none'); assert.equal(rows[1].style.display, '');
link.handlers.click();
assert.equal(feedbackFilter.value, ''); assert.equal(rows[0].style.display, '');
assert.equal(details.open, true); assert.equal(history.open, true);
ids.showAIWithoutRecurrence.handlers.click();
assert.equal(feedbackFilter.value, 'ai-clear'); assert.equal(sourceFilter.value, 'ai');
assert.equal(rows[0].style.display, ''); assert.equal(rows[1].style.display, 'none');
assert.equal(rows[2].style.display, 'none');
assert.equal(ids.findingFilterStatus.textContent, '1 of 3 findings shown.');
sourceFilter.value = 'vale'; sourceFilter.handlers.change();
assert.match(ids.findingFilterStatus.textContent, /No findings match/);
feedbackFilter.handlers.change();
assert.equal(sourceFilter.value, 'ai'); assert.equal(rows[0].style.display, '');
ids.showAllFindings.handlers.click();
assert.equal(sourceFilter.value, ''); assert.equal(rows[2].style.display, '');
''')
        subprocess.run(['node', str(harness), str(filter_script)], check=True, capture_output=True)

    def test_ai_without_recurrence_filter_classification(self):
        def candidate(verdict):
            return {'comparison': {'verdict': verdict}} if verdict else {'comparison': None}
        for verdicts, confirmed, source, expected in [
            ([], False, 'ai', True),
            (['different_complaint'], False, 'ai', True),
            (['different_complaint', 'different_complaint'], False, 'ai', True),
            (['same_complaint'], False, 'ai', False),
            (['uncertain'], False, 'ai', False),
            ([None], False, 'ai', False),
            (['different_complaint', 'uncertain'], False, 'ai', False),
            (['different_complaint', 'same_complaint'], False, 'ai', False),
            (['different_complaint', None], False, 'ai', False),
            ([], True, 'ai', False),
            ([], False, 'vale', False),
        ]:
            with self.subTest(verdicts=verdicts, confirmed=confirmed, source=source):
                issue = {'source': source, 'recurrence_candidates': [candidate(v) for v in verdicts],
                         'feedback_link_confirmation': {'decision': 'confirmed'} if confirmed else None}
                self.assertEqual(review.ai_without_recurrence_concerns(issue), expected)
        self.decide('rejected')
        self.attach()
        self.assertTrue(review.ai_without_recurrence_concerns(self.new))

    def test_link_cli_without_api_key(self):
        self.attach()
        # Use an actual verified temporary source under the repository so the
        # CLI exercises source binding without mocking its command dispatch.
        with tempfile.TemporaryDirectory(dir=review.PROJECT_ROOT / '.qa') as directory:
            source = Path(directory) / 'source.md'
            source.write_text(self.source)
            relative = source.relative_to(review.PROJECT_ROOT).as_posix()
            self.old['file'] = self.new['file'] = relative
            self.record['latest_finding'] = copy.deepcopy(self.old)
            self.registry.write_text(json.dumps(self.store))
            self.attach()
            env = {k: v for k, v in os.environ.items() if k != 'DEEPSEEK_API_KEY'}
            result = subprocess.run([sys.executable, str(Path(review.__file__)), 'link',
                '--report', str(self.report), '--issue', 'qa-new', '--previous', 'qa-old',
                '--decision', 'confirmed', '--reason', 'Same complaint',
                '--feedback-file', str(self.registry)], capture_output=True, text=True, env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('does not dismiss', result.stdout)


if __name__ == '__main__':
    unittest.main()
