import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import taxonomy as tools
import taxonomy_ai

ROOT = Path(__file__).resolve().parents[2]


class LandingPageTaxonomyTests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = tools.load_and_validate_taxonomy(ROOT)

    def test_landing_pages_have_only_the_landing_tag(self):
        for folder in ("case-studies", "docs-samples", "skills", "tools"):
            front, _ = tools.load_front_matter(ROOT / "docs" / folder / "index.md")
            self.assertEqual(front["type"], ["landing-page"])
            self.assertEqual(front["tags"], ["landing-page"])
            self.assertEqual(front["lifecycle"], ["current"])
            self.assertEqual(tools.validate_front_matter_data(front, folder, self.taxonomy), [])
            for field in ("audiences", "topics", "technologies", "organisations"):
                self.assertNotIn(field, front)

    def test_subject_metadata_is_rejected_and_sync_cannot_restore_subject_tags(self):
        front, _ = tools.load_front_matter(ROOT / "docs/tools/index.md")
        front["topics"] = ["documentation-engineering"]
        front["tags"] = ["documentation-engineering"]
        tools.sync_front_matter_tags(front, self.taxonomy)
        self.assertEqual(front["tags"], ["landing-page"])
        errors = tools.validate_front_matter_data(front, "landing", self.taxonomy)
        self.assertTrue(any("0..0" in error for error in errors))

    def test_public_tag_and_editor_choices_are_generated(self):
        tags = tools.round_trip_yaml().load(tools.render_docusaurus_tags(self.taxonomy))
        self.assertEqual(tags["landing-page"]["label"], "Landing page")
        fields = tools.fields_for_content_type(self.taxonomy, "landing-page")
        taxonomy_fields = {field["name"] for field in fields if field["type"] == "taxonomy"}
        self.assertEqual(taxonomy_fields, {"type", "lifecycle"})

    def test_ai_cannot_classify_landing_pages_by_subject(self):
        front, body = tools.load_front_matter(ROOT / "docs/tools/index.md")
        metadata = copy.deepcopy(dict(front))
        metadata["topics"] = ["documentation-engineering"]
        metadata["technologies"] = ["docusaurus"]
        result = taxonomy_ai.validate_ai_result(
            {"metadata": metadata, "proposed_taxonomy_terms": []}, self.taxonomy, body, front)
        for field in ("audiences", "topics", "technologies", "organisations"):
            self.assertEqual(result["metadata"][field], [])


if __name__ == "__main__":
    unittest.main()
