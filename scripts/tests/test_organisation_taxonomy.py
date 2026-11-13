import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import taxonomy as tools
import taxonomy_ai
from generate_taxonomy import build_taxonomy
from apply_organisation_metadata import plan
from upgrade_taxonomy_v3 import upgrade

ROOT = Path(__file__).resolve().parents[2]


class OrganisationTaxonomyTests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = tools.load_and_validate_taxonomy(ROOT)

    def test_upgrade_preserves_all_existing_dimensions(self):
        old = copy.deepcopy(self.taxonomy)
        old["version"] = 2
        del old["dimensions"]["organisations"]
        candidate = upgrade(old)
        self.assertEqual(candidate["version"], 3)
        for dimension, value in old["dimensions"].items():
            self.assertEqual(candidate["dimensions"][dimension], value)
        self.assertEqual(old["version"], 2)
        self.assertNotIn("organisations", old["dimensions"])
        tools.validate_taxonomy_schema(candidate, ROOT / tools.SCHEMA_PATH)

    def test_documents_without_organisations_remain_valid(self):
        front, _ = tools.load_front_matter(ROOT / "docs/case-studies/DocusaurusPortfolio.md")
        self.assertNotIn("organisations", front)
        self.assertEqual(tools.validate_front_matter_data(front, "example", self.taxonomy), [])

    def test_unknown_duplicate_and_scalar_values_are_rejected(self):
        front, _ = tools.load_front_matter(ROOT / "docs/case-studies/DocusaurusPortfolio.md")
        for values in (["unknown-company"], ["amx", "amx"], ["amx", "paysafe"], "amx"):
            with self.subTest(values=values):
                candidate = copy.deepcopy(front)
                candidate["organisations"] = values
                self.assertTrue(tools.validate_front_matter_data(candidate, "example", self.taxonomy))

    def test_vocabulary_migration_adds_only_four_organisations(self):
        path = ROOT / "taxonomy/migrations/2026-11-13-work-organisations.yml"
        migration = tools.load_yaml(path)
        old = copy.deepcopy(self.taxonomy)
        old["dimensions"]["organisations"]["terms"] = {}
        tools.validate_migration_schema(migration, ROOT / tools.MIGRATION_SCHEMA_PATH)
        tools.validate_migration_semantics(old, migration, path)
        tools.validate_migration_preconditions(old, migration)
        candidate, replacements, deprecated = tools.build_migrated_taxonomy(old, migration)
        self.assertEqual(set(candidate["dimensions"]["organisations"]["terms"]),
                         {"amx", "mastercard", "morgan-stanley", "paysafe"})
        self.assertFalse(replacements)
        self.assertFalse(deprecated)
        for dimension in old["dimensions"]:
            if dimension != "organisations":
                self.assertEqual(candidate["dimensions"][dimension], old["dimensions"][dimension])

    def test_mapping_is_idempotent_on_migrated_corpus(self):
        manifest = json.loads((ROOT / "taxonomy/migrations/2026-11-13-organisation-metadata.json").read_text())
        self.assertEqual(plan(ROOT, manifest, self.taxonomy), {})

    def test_mapping_preflights_evidence_and_preserves_body(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            source = ROOT / "docs/case-studies/DocusaurusPortfolio.md"
            path = root / "docs/example.md"
            original = source.read_text()
            path.write_text(original)
            entry = {"file": "docs/example.md", "expect": [], "organisations": ["amx"],
                     "scope": "whole-page-single-employer",
                     "evidence": {"amx": "I designed and built this portfolio"}}
            manifest = {"version": 1, "taxonomy_version": 3, "documents": [entry]}
            changes = plan(root, manifest, self.taxonomy)
            self.assertEqual(path.read_text(), original)
            before = tools.split_front_matter(original)
            after = tools.split_front_matter(changes[path.resolve()])
            self.assertEqual(before[2], after[2])
            metadata = tools.round_trip_yaml().load(after[1])
            self.assertEqual(metadata["organisations"], ["amx"])
            if self.taxonomy["dimensions"]["organisations"]["docusaurus_tags"]:
                self.assertIn("amx", metadata["tags"])
            else:
                self.assertEqual(after[1], "organisations:\n  - amx\n" + before[1])
            entry["evidence"]["amx"] = "Absent evidence"
            with self.assertRaises(tools.ValidationError):
                plan(root, manifest, self.taxonomy)
            self.assertEqual(path.read_text(), original)

    def test_ai_cannot_add_or_remove_human_assignments(self):
        for filename, values in (("docs/case-studies/DocusaurusPortfolio.md", ["amx"]),
                                 ("docs/case-studies/ScalingADeveloperDocsPlatform.md", [])):
            with self.subTest(filename=filename):
                front, _ = tools.load_front_matter(ROOT / filename)
                metadata = {d["metadata_field"]: list(front.get(d["metadata_field"], []))
                            for d in self.taxonomy["dimensions"].values()}
                metadata["organisations"] = values
                with patch.object(tools, "write_front_matter") as writer:
                    with self.assertRaisesRegex(ValueError, "human-controlled"):
                        taxonomy_ai.apply_results(ROOT, self.taxonomy, [{"file": filename, "metadata": metadata}])
                    writer.assert_not_called()

    def test_ai_normalisation_preserves_reviewed_organisations(self):
        front, body = tools.load_front_matter(ROOT / "docs/case-studies/ScalingADeveloperDocsPlatform.md")
        metadata = {d["metadata_field"]: list(front.get(d["metadata_field"], []))
                    for d in self.taxonomy["dimensions"].values()}
        metadata["organisations"] = ["amx"]
        result = taxonomy_ai.validate_ai_result(
            {"metadata": metadata, "proposed_taxonomy_terms": []}, self.taxonomy, body, front)
        self.assertEqual(result["metadata"]["organisations"], ["morgan-stanley"])

    def test_ai_taxonomy_regeneration_preserves_organisation_catalogue(self):
        terms = {name: self.taxonomy["dimensions"][name]["terms"]
                 for name in ("content_types", "audiences", "topics", "technologies")}
        organisations = self.taxonomy["dimensions"]["organisations"]
        candidate = build_taxonomy(terms, "2026-11-13", organisations)
        self.assertEqual(candidate["dimensions"]["organisations"], organisations)
        self.assertIsNot(candidate["dimensions"]["organisations"], organisations)

    def test_only_seven_employer_specific_documents_are_assigned(self):
        from collections import Counter
        counts = Counter()
        assigned = []
        for path in tools.all_docs(ROOT):
            front, _ = tools.load_front_matter(path)
            values = front.get("organisations", [])
            if values:
                self.assertEqual(len(values), 1)
                self.assertIn(path.parent.name, {"case-studies", "docs-samples"})
                counts.update(values)
                assigned.append(path)
        self.assertEqual(len(assigned), 7)
        self.assertEqual(dict(counts), {"amx": 1, "mastercard": 2, "morgan-stanley": 2, "paysafe": 2})
        removal = json.loads((ROOT / "taxonomy/migrations/2026-11-13-remove-overview-organisations.json").read_text())
        self.assertEqual(plan(ROOT, removal, self.taxonomy), {})
        for entry in removal["documents"]:
            front, _ = tools.load_front_matter(ROOT / entry["file"])
            self.assertNotIn("organisations", front)
            self.assertFalse(set(front["tags"]) & set(counts))

    def test_assignment_mapping_requires_whole_page_review(self):
        manifest = json.loads((ROOT / "taxonomy/migrations/2026-11-13-organisation-metadata.json").read_text())
        del manifest["documents"][0]["scope"]
        with self.assertRaisesRegex(tools.ValidationError, "whole-page"):
            plan(ROOT, manifest, self.taxonomy)


if __name__ == "__main__":
    unittest.main()
