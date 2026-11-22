from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qa_checks.tooltip import TooltipAuditCheck
from qa_policy import evaluate_ci, is_ci_threshold_eligible
from taxonomy_tooltips import ROOT, scan


class TooltipQATests(unittest.TestCase):
    def test_occurrence_appears_in_qa_without_affecting_gate(self):
        file = ROOT / "docs/case-studies/RagSearchCloudArchitecture.md"
        document = file.relative_to(ROOT).as_posix()
        report = scan(ROOT, files=[document])
        mention = next(item for item in report["documents"][document]["candidates"]
                       if item["term_id"] == "requests" and item["matched_text"] == "Requests")
        mention["current_decision"] = None
        with patch("qa_checks.tooltip.scan", return_value=report):
            result = TooltipAuditCheck(ROOT).run([file])
        self.assertEqual(result.errors, [])
        mentions = [issue for issue in result.issues if issue["category"] == "tooltip-mention"]
        self.assertTrue(mentions)
        rejected_context = next(issue for issue in mentions if "Requests are validated" in issue["original"])
        self.assertIn("pos_evidence", rejected_context["tooltip_evidence"])
        self.assertTrue(all(not is_ci_threshold_eligible(issue) for issue in result.issues))
        self.assertTrue(evaluate_ci(result.issues, result.errors, 0, 0, 0)["passed"])

    def test_scanner_failure_is_advisory(self):
        with patch("qa_checks.tooltip.scan", side_effect=OSError("Node unavailable")):
            result = TooltipAuditCheck(ROOT).run([ROOT / "docs/misc/OptimusRICE.md"])
        self.assertEqual(result.errors, [])
        self.assertEqual(result.issues[0]["category"], "tooltip-unavailable")
        self.assertTrue(evaluate_ci(result.issues, result.errors, 0, 0, 0)["passed"])
