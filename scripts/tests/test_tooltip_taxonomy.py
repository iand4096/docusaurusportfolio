"""Deterministic semantic tooltip gate regressions."""

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import taxonomy
import taxonomy_tooltips as tooltips


class TooltipTaxonomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = tooltips.scan(tooltips.ROOT, strict=True)

    def test_rice_definition_finding_detects_old_description_and_verifies_resolution(self):
        records = tooltips.read_artifact(tooltips.ROOT, tooltips.DEFINITIONS)["findings"]
        record = records["rice-definition-mismatch"]
        migration = taxonomy.load_yaml(tooltips.ROOT / record["resolution_migration"])
        old = copy.deepcopy(self.report)
        old["terms"]["rice"]["description"] = migration["changes"]["technologies"]["update"]["rice"]["expect"]["description"]
        old["terms"]["rice"]["definition_hash"] = record["previous_definition_fingerprint"]
        finding = next(item for item in tooltips.definition_findings(old) if item["term_id"] == "rice")
        self.assertEqual(finding["status"], "needs_review")
        self.assertIn("Calculation Environment", finding["evidence"][0]["excerpt"])
        self.assertFalse(tooltips.definition_findings(self.report))
        self.assertFalse(tooltips.definition_errors(tooltips.ROOT, self.report))

    def test_resolved_taxonomy_requires_migration_evidence(self):
        records = tooltips.read_artifact(tooltips.ROOT, tooltips.DEFINITIONS)
        entry = records["findings"]["rice-definition-mismatch"]
        del entry["resolution_migration"]
        with patch.object(tooltips, "read_artifact", return_value=records):
            self.assertIn("Missing definition correction migration: rice-definition-mismatch",
                          tooltips.definition_errors(tooltips.ROOT, self.report))

    def test_preflight_checks_technology_changes_but_skips_unrelated_changes(self):
        original = taxonomy.load_yaml(tooltips.ROOT / taxonomy.TAXONOMY_PATH)
        candidate = copy.deepcopy(original)
        candidate["dimensions"]["technologies"]["terms"]["python"]["description"] += " Revised."
        with patch.object(tooltips, "check") as check:
            tooltips.preflight(tooltips.ROOT, original, original, {})
            check.assert_not_called()
            tooltips.preflight(tooltips.ROOT, original, candidate, {})
            check.assert_called_once_with(tooltips.ROOT, original, candidate, {})
