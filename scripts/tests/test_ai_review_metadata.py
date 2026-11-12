import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ai_docs_review as review


CONTENT = """---
title: API documentation
description: >-
  A reader-facing description.
technologies: [curl, openapi]
tags:
  - curl
slug: /internal-id
sidebar_custom_props:
  sampleCard:
    description: Card description.
    highlights:
      - A visible highlight.
    internal_id: hidden-id
---

Using cURL to test endpoints.
"""


class ProseMetadataTests(unittest.TestCase):
    def test_only_prose_metadata_is_retained_at_original_lines(self):
        filtered = review.ai_review_content(CONTENT)
        for hidden in ('[curl, openapi]', '  - curl', '/internal-id', 'hidden-id'):
            self.assertNotIn(hidden, filtered)
        for visible in ('API documentation', 'A reader-facing description.',
                        'Card description.', 'A visible highlight.',
                        'Using cURL to test endpoints.'):
            self.assertIn(visible, filtered)
            self.assertEqual(review.find_source_line(CONTENT, visible),
                             review.find_source_line(filtered, visible))
        self.assertEqual(len(CONTENT.splitlines()), len(filtered.splitlines()))

    def test_crlf_and_documents_without_front_matter(self):
        crlf = CONTENT.replace('\n', '\r\n')
        self.assertEqual(review.ai_review_content(crlf).count('\r\n'), crlf.count('\r\n'))
        self.assertEqual(review.ai_review_content('Plain body\n'), 'Plain body\n')

    def test_inline_mapping_does_not_expose_neighbouring_technical_values(self):
        source = '---\nsidebar_custom_props: {sampleCard: {description: Visible prose, internal_id: secret-id}}\n---\nBody\n'
        filtered = review.ai_review_content(source)
        self.assertIn('Visible prose', filtered)
        self.assertNotIn('secret-id', filtered)
        self.assertNotIn('internal_id', filtered)
        self.assertEqual(len(source.splitlines()), len(filtered.splitlines()))

    def test_front_matter_boundaries_and_body_are_preserved(self):
        for ending in ('---', '...'):
            for newline in ('\n', '\r\n'):
                source = CONTENT.replace('---\n\nUsing', ending + '\n\nUsing').replace('\n', newline)
                filtered = review.ai_review_content(source)
                original_lines = source.splitlines(keepends=True)
                filtered_lines = filtered.splitlines(keepends=True)
                end = next(i for i in range(1, len(original_lines))
                           if original_lines[i].strip() == ending)
                self.assertEqual(filtered_lines[0], original_lines[0])
                self.assertEqual(filtered_lines[end:], original_lines[end:])
                self.assertEqual(len(filtered), len(source))

    def test_skill_cards_include_prose_but_hide_technical_fields(self):
        source = CONTENT.replace('sampleCard:', 'skillCard:')
        filtered = review.ai_review_content(source)
        self.assertIn('Card description.', filtered)
        self.assertIn('A visible highlight.', filtered)
        self.assertNotIn('hidden-id', filtered)

    def test_published_false_positive_files_keep_delimiters_and_body(self):
        for name in ('docs/skills/AIandDocumentation.md',
                     'docs/tools/ContainersAndCloudNative.md'):
            source = (review.PROJECT_ROOT / name).read_text()
            filtered = review.ai_review_content(source)
            self.assertEqual(filtered.splitlines()[0], '---')
            end = source.splitlines().index('---', 1)
            self.assertEqual(filtered.splitlines()[end:], source.splitlines()[end:])

    def test_all_ai_entry_points_filter_metadata(self):
        path = Path('example.md')
        with patch.object(review, 'request_review', return_value={'issues': []}) as request:
            review.GrammarReview().run_page(path, CONTENT, 'unused')
            review.RepetitionReview().run_page(path, CONTENT, 'unused')
            review.RepetitionReview().run_site([path], {str(path): CONTENT}, 'unused')
            review.SiteWideConsistencyReview().run_site([path], {str(path): CONTENT}, 'unused')
        self.assertEqual(request.call_count, 4)
        for call in request.call_args_list:
            self.assertIn('filtering artefacts', call.args[0])
            self.assertIn('body after the closing delimiter is unchanged', call.args[0])
            prompt = call.args[1]
            self.assertNotIn('[curl, openapi]', prompt)
            self.assertNotIn('hidden-id', prompt)
            self.assertIn('Card description.', prompt)
            self.assertIn('Using cURL to test endpoints.', prompt)


if __name__ == '__main__':
    unittest.main()
