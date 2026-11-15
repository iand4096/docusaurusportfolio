import contextlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ai_docs_review as review


PROJECT = Path(__file__).resolve().parents[2]


class ParserIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "node_modules").symlink_to(PROJECT / "node_modules", target_is_directory=True)
        shutil.copy(PROJECT / ".remarkrc.mjs", self.root / ".remarkrc.mjs")
        (self.root / "docs").mkdir()
        shutil.copy(PROJECT / "docs/.remarkrc.mjs", self.root / "docs/.remarkrc.mjs")
        self.root_patch = patch.object(review, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def run_remark(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        with contextlib.chdir(self.root):
            return review.RemarkCheck().run_files(
                [path], executable=str(PROJECT / "node_modules/.bin/remark")
            )

    def test_repository_readme_accepts_markdown_autolinks(self):
        issues = self.run_remark(
            "src/components/Example/README.md",
            "# Example\n\n<http://127.0.0.1:3000/preview>\n",
        )
        self.assertEqual(issues, [])

    def test_docusaurus_md_reports_nested_jsx_error_at_real_line(self):
        issues = self.run_remark("docs/broken.md", '# Example\n\n<Widget label=="bad" />\n')
        self.assertEqual(len(issues), 1)
        issue = issues[0]
        self.assertEqual(issue["line"], 3)
        self.assertEqual(issue["severity"], "high")
        self.assertIn("Unexpected character", issue["message"])
        self.assertIn("label==", issue["original"])
        self.assertIn("parser", issue["suggestion"])
        self.assertNotIn("rule `remark`", issue["suggestion"])

    def test_docusaurus_mdx_keeps_jsx_lint_rules(self):
        issues = self.run_remark(
            "docs/duplicate.mdx", '# Example\n\n<Widget label="one" label="two" />\n'
        )
        self.assertTrue(any(i["category"] == "mdx-jsx-unique-attribute-name" for i in issues))

    def test_generated_reports_are_not_reviewed_as_articles(self):
        for relative in ["README.md", "docs/article.md", "reports/see-also.md"]:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Example\n", encoding="utf-8")
        selected = {p.relative_to(self.root).as_posix() for p in review.markdown_files()}
        self.assertIn("README.md", selected)
        self.assertIn("docs/article.md", selected)
        self.assertNotIn("reports/see-also.md", selected)

    def test_local_preview_link_exclusions_do_not_hide_public_hosts(self):
        patterns = [re.compile(line) for line in (PROJECT / ".lycheeignore").read_text().splitlines()
                    if line.strip() and not line.startswith("#")]
        for url in ["http://localhost:3000/page", "http://127.0.0.1:3000/page",
                    "https://[::1]:3000/page", "http://localhost"]:
            self.assertTrue(any(p.search(url) for p in patterns), url)
        for url in ["https://example.com", "https://localhost.example.com",
                    "https://127.0.0.1.example.com", "https://example.com/localhost"]:
            self.assertFalse(any(p.search(url) for p in patterns), url)

    @unittest.skipUnless(shutil.which("vale") and shutil.which("mdx2vast"),
                         "Vale and mdx2vast are required for the real MDX regression check")
    def test_vale_reads_mdx_imports_and_still_checks_visible_prose(self):
        path = self.root / "docs/example.mdx"
        path.write_text(
            'import One from "one";\nimport Two from "two";\n'
            'import CodeBlock from "@theme/CodeBlock";\n\n'
            '# Example\n\nVisible prose with and/or in it.\n\n'
            '<CodeBlock language="jsx">{"import One from \\\"one\\\";\\n<One />"}</CodeBlock>\n',
            encoding="utf-8",
        )
        result = subprocess.run(
            [shutil.which("vale"), "--config", str(PROJECT / ".vale.ini"),
             "--output=JSON", "--no-exit", str(path)],
            cwd=PROJECT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        alerts = [alert for values in report.values() for alert in values]
        self.assertTrue(any(alert.get("Check") == "Portfolio.AndOr" for alert in alerts), report)


if __name__ == "__main__":
    unittest.main()
