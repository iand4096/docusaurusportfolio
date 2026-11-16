import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ai_docs_review as review


class Buttons(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.buttons = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'button' and 'data-source-filter' in attrs:
            self.buttons[attrs['data-source-filter']] = attrs


class SourceFilterTests(unittest.TestCase):
    def test_zero_finding_checks_are_included_and_unrun_checks_are_omitted(self):
        html = review.source_filter_buttons([{'source': 'ai'}], [],
            {'checks': ['GrammarReview', 'ValeCheck', 'LtexCheck']})
        buttons = Buttons(html).buttons
        self.assertEqual(set(buttons), {'', 'ai', 'vale', 'ltex'})
        self.assertEqual(buttons['']['aria-pressed'], 'true')
        self.assertEqual(buttons['vale']['aria-pressed'], 'false')
        self.assertIn('writing style', buttons['vale']['title'])
        self.assertNotIn('findings', buttons['vale']['title'])
        self.assertNotRegex(buttons['vale']['title'], r'\d')
        self.assertIn('source-vale', buttons['vale']['class'])
        self.assertLess(html.index('data-source-filter="ai"'), html.index('source-separator'))
        self.assertLess(html.index('source-separator'), html.index('data-source-filter="vale"'))

    def test_legacy_reports_recover_sources_from_findings_and_errors(self):
        html = review.source_filter_buttons([{'source': 'remark'}],
            [{'check': 'LycheeCheck'}], {})
        self.assertEqual(set(Buttons(html).buttons), {'', 'remark', 'lychee'})
        self.assertNotIn('source-separator', html)

    def test_static_tooltip_describes_its_checks(self):
        html = review.source_filter_buttons([], [], {'checks': ['AccessibilityCheck', 'LinkCheck']})
        self.assertEqual(set(Buttons(html).buttons), {'', 'static'})
        title = Buttons(html).buttons['static']['title']
        self.assertIn('local links', title)
        self.assertIn('accessibility', title)


if __name__ == '__main__':
    unittest.main()
