import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ai_docs_review as review

BODY = 'I built a tool. These instructions explain how to run it.'


def finding(category='portfolio'):
    return dict(severity='medium', confidence='high', type='defect', category=category,
                line=1, original='I built a tool.', message='The contribution needs an outcome.',
                suggestion='Explain the outcome.', source='ai')


class GenreReviewTests(unittest.TestCase):
    def test_repository_genres_and_absolute_paths(self):
        cases = {
            'docs/case-studies/example.md': 'case-study',
            'docs/docs-samples/example.mdx': 'documentation-sample',
            'docs/skills/example.md': 'skill-overview',
            'docs/tools/example.md': 'tool-overview',
            'docs/tools/index.md': 'landing-page',
            'src/pages/index.md': 'homepage',
            'README.md': 'technical-readme',
            'src/pages/browse/README.md': 'technical-readme',
            'knowledge-api/README.md': 'technical-readme',
            'knowledge-api/OPERATIONS-linux.md': 'operations-guide',
            'src/components/CapabilityGrid/README.md': 'component-guide',
            'docs/implementation-details/taxonomy.md': 'implementation-guide',
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(review.document_genre(path, BODY), expected)
                self.assertEqual(review.document_genre(review.PROJECT_ROOT / path, BODY), expected)

    def test_metadata_fallback_does_not_override_technical_paths(self):
        content = '---\ntype: [case-study]\n---\n' + BODY
        self.assertEqual(review.document_genre('custom.md', content), 'case-study')
        self.assertEqual(review.document_genre('knowledge-api/README.md', content), 'technical-readme')
        self.assertEqual(review.document_genre('custom.md', BODY), 'general-document')

    def test_portfolio_review_skips_non_narrative_pages_without_ai_calls(self):
        with patch.object(review, 'request_review') as request:
            for path in ['docs/skills/example.md', 'docs/tools/example.md',
                         'README.md', 'knowledge-api/OPERATIONS.md',
                         'src/components/example/README.md', 'src/pages/index.md']:
                self.assertEqual(review.PortfolioReview().run_page(Path(path), BODY, 'unused'), [])
            request.assert_not_called()

    def test_metadata_genre_survives_editorial_masking(self):
        content = '---\ntype: [case-study]\n---\n' + BODY
        with patch.object(review, 'request_review', return_value={'issues': [finding()]}) as request:
            result = review.PortfolioReview().run_page(Path('custom.md'), content, 'unused')
        self.assertEqual(len(result), 1)
        self.assertIn('DOCUMENT GENRE: case-study', request.call_args.args[1])
        self.assertNotIn('type: [case-study]', request.call_args.args[1])
        self.assertEqual(result[0]['line'], 4)

    def test_site_outputs_cannot_apply_portfolio_requirements_to_readmes(self):
        paths = [Path('knowledge-api/README.md'), Path('docs/case-studies/example.md')]
        issues = [{**finding(), 'file': str(path)} for path in paths]
        contents = {str(path): BODY for path in paths}
        result = review.validate_site_ai_issues(issues, paths, contents, {'portfolio'})
        self.assertEqual([issue['file'] for issue in result], ['docs/case-studies/example.md'])

    def test_language_defects_are_not_hidden_by_genre(self):
        for path in ['docs/tools/example.md', 'knowledge-api/README.md']:
            self.assertIsNotNone(review.normalise_ai_issue(finding('grammar'), BODY, path, {'grammar'}))

    def test_every_request_receives_genre_context(self):
        path = Path('docs/tools/example.md')
        contents = {str(path): BODY}
        with patch.object(review, 'request_review', return_value={'issues': []}) as request:
            review.GrammarReview().run_page(path, BODY, 'unused')
            review.StructureReview().run_page(path, BODY, 'unused')
            review.RepetitionReview().run_page(path, BODY, 'unused')
            review.RepetitionReview().run_site([path], contents, 'unused')
            review.SiteWideConsistencyReview().run_site([path], contents, 'unused')
        self.assertEqual(request.call_count, 5)
        for call in request.call_args_list:
            self.assertIn('DOCUMENT GENRE: tool-overview', call.args[1])
            self.assertIn('not case studies', call.args[0])

    def test_mixed_site_keeps_each_declared_genre(self):
        paths = [Path('custom.md'), Path('knowledge-api/README.md')]
        contents = {'custom.md': '---\ntype: [case-study]\n---\n' + BODY,
                    'knowledge-api/README.md': BODY}
        issues = [{**finding(), 'file': str(path)} for path in paths]
        with patch.object(review, 'request_review', return_value={'issues': issues}) as request:
            result = review.SiteWideConsistencyReview().run_site(paths, contents, 'unused')
        self.assertEqual([issue['file'] for issue in result], ['custom.md'])
        self.assertIn('DOCUMENT GENRE: technical-readme', request.call_args.args[1])
        self.assertIn('DOCUMENT GENRE: case-study', request.call_args.args[1])


if __name__ == '__main__':
    unittest.main()
