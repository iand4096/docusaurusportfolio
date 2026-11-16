"""Regression checks for the deterministic findings in QA run 80b5ada5e718."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ai_docs_review as review


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


class LtexContextTests(unittest.TestCase):
    def diagnostic(self, text, token, rule, message='Grammar finding'):
        return review.normalise_ltex_diagnostic({
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
            self.assertIsNone(self.diagnostic(text, command, 'UPPERCASE_SENTENCE_START'))
            self.assertIsNotNone(self.diagnostic(text, 'invalid', 'UPPERCASE_SENTENCE_START'))

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
            self.assertEqual(review.parse_ltex_output(output, [path]), [])
            self.assertTrue(review.ltex_output_contains_only_ignored_syntax(output, [path]))
            self.assertFalse(review.ltex_output_contains_only_ignored_syntax('unknown renderer', [path]))


if __name__ == '__main__':
    unittest.main()
