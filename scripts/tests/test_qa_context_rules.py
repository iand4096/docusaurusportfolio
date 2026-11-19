"""Regression checks for the deterministic findings in QA run 80b5ada5e718."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ai_docs_review as review
from qa_checks import ltex
from qa_checks.vale import ValeCheck


class RouteLinkTests(unittest.TestCase):
    def test_pages_resolve_queries_fragments_and_trailing_slashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in ['src/pages/explore/index.tsx', 'src/pages/about.mdx', 'static/img/logo.svg']:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('fixture')
            with patch.object(review, 'ROOT', root):
                check = review.LinkCheck()
                for target in ['/explore?view=browse', '/explore/?view=browse#filters', '/about', '/img/logo.svg']:
                    self.assertTrue(check._local_target_exists(root / 'docs/article.md', target), target)
                for target in ['/missing?view=browse', '/src/pages/explore', '/explore/missing', '/img/missing.svg']:
                    self.assertFalse(check._local_target_exists(root / 'docs/article.md', target), target)
                self.assertTrue(check._local_target_exists(root / 'README.md', 'src/'))


class FileCheckExecutionTests(unittest.TestCase):
    def test_preflight_failure_is_reported_and_following_adapter_still_runs(self):
        paths = [Path('fixture.md')]
        ltex_check = ltex.LtexCheck()
        vale_check = ValeCheck()
        finding = {'source': 'vale'}
        with patch.object(ltex_check, 'preflight', side_effect=RuntimeError('LTeX+ unavailable')), \
             patch.object(ltex_check, 'run_files') as ltex_run, \
             patch.object(vale_check, 'preflight', return_value='/test/vale'), \
             patch.object(vale_check, 'run_files', return_value=[finding]) as vale_run:
            result = review.run_file_checks(paths, [ltex_check, vale_check])

        ltex_run.assert_not_called()
        vale_run.assert_called_once_with(paths, executable='/test/vale')
        self.assertEqual(result.issues, [finding])
        self.assertEqual(result.errors, [
            {'check': 'LtexCheck', 'file': '<ltex>', 'error': 'LTeX+ unavailable'},
        ])


class LtexContextTests(unittest.TestCase):
    def diagnostic(self, text, token, rule, message='Grammar finding'):
        return ltex.normalise_ltex_diagnostic({
            'line': 1, 'column': text.index(token) + 1, 'severity': 'warning',
            'message': f'{message} [{rule}]',
        }, [], Path('fixture.md'), text)

    def test_preserve_official_names_but_check_other_words(self):
        self.assertIsNone(self.diagnostic('Paysafe Developer Center', 'Center', 'MORFOLOGIK_RULE_EN_GB', "'Center': spelling"))
        self.assertIsNotNone(self.diagnostic('Visit the Center', 'Center', 'MORFOLOGIK_RULE_EN_GB', "'Center': spelling"))
        self.assertIsNotNone(self.diagnostic('Developer Center has a typo', 'typo', 'MORFOLOGIK_RULE_EN_GB', "'typo': spelling"))
        for name in ['SIL Open Font License 1.1', 'MIT License']:
            self.assertIsNone(self.diagnostic(name, 'License', 'LICENCE_LICENSE_NOUN_SINGULAR'))
        self.assertIsNotNone(self.diagnostic('Read the License terms', 'License', 'LICENCE_LICENSE_NOUN_SINGULAR'))

    def test_code_article_exception_is_local_and_narrow(self):
        self.assertIsNone(self.diagnostic('Pass an `items` array.', 'an', 'EN_A_VS_AN'))
        self.assertIsNotNone(self.diagnostic('Pass an `widget` object.', 'an', 'EN_A_VS_AN'))
        self.assertIsNotNone(self.diagnostic('Pass an `items` array to a editor.', 'a editor', 'EN_A_VS_AN'))

    def test_command_labels_keep_case_but_surrounding_prose_is_checked(self):
        for command in ['npm ci', '`npm install`', '`pip install: additional indexes`']:
            text = f'| [{command}](https://example.com) | invalid prose. |'
            self.assertIsNone(self.diagnostic(text, command.strip('`').split()[0], 'UPPERCASE_SENTENCE_START'))
            self.assertIsNotNone(self.diagnostic(text, 'invalid', 'UPPERCASE_SENTENCE_START'))

    def test_command_prefix_does_not_exempt_prose_inside_the_link_label(self):
        for command in ['npm', 'pip']:
            for quote in ['', '`']:
                text = f'[{quote}{command} install{quote}. this sentence starts lowercase](https://example.com)'
                self.assertIsNone(self.diagnostic(text, command, 'UPPERCASE_SENTENCE_START'))
                self.assertIsNotNone(self.diagnostic(text, 'this', 'UPPERCASE_SENTENCE_START'))
                self.assertIsNotNone(self.diagnostic(text, 'install', 'UPPERCASE_SENTENCE_START'))

    def test_repeated_table_values_are_independent_but_cell_errors_remain(self):
        for rule in ['PHRASE_REPETITION', 'OK_OK_COMMA']:
            self.assertIsNone(self.diagnostic('| API | Yes | Yes | No |', 'Yes', rule))
            self.assertIsNone(self.diagnostic('| UI | No | No | No | Yes |', 'No', rule))
            self.assertIsNotNone(self.diagnostic('| API | Yes Yes | No |', 'Yes', rule))
        self.assertIsNotNone(self.diagnostic('| API | Yes | Yes | a error |', 'a error', 'EN_A_VS_AN'))
        self.assertIsNotNone(self.diagnostic('Yes Yes is repeated.', 'Yes', 'PHRASE_REPETITION'))

    def test_filtered_diagnostics_are_not_treated_as_an_unparseable_run(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'example.md'
            path.write_text('Pass an `items` array.\n')
            output = f'{path}:1:6: warning: Use a [EN_A_VS_AN]\n'
            self.assertEqual(ltex.parse_ltex_output(output, [path]), [])
            self.assertTrue(ltex.ltex_output_contains_only_ignored_syntax(output, [path]))
            self.assertFalse(ltex.ltex_output_contains_only_ignored_syntax('unknown renderer', [path]))


if __name__ == '__main__':
    unittest.main()
