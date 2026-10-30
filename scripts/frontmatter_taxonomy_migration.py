#!/usr/bin/env python3
"""Create a review-only taxonomy v2 expansion migration from a saved DeepSeek review.

Front Matter CMS passes workspace root, document path and (optionally) front matter
JSON as argv[1:4]. The JSON is intentionally ignored: only the saved review
artifact, never unreviewed editor state, can propose vocabulary changes.

No taxonomy, document front matter or generated projection is modified.
"""
from __future__ import annotations

import json
import jsonschema
import re
import sys
from datetime import date
from pathlib import Path

from ruamel.yaml import YAML
from frontmatter_taxonomy import taxonomy_review_paths

ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def generate(root: Path, document: Path) -> Path | None:
    root = root.resolve()
    document = document.resolve()
    # Shared review path routine also confines the document to workspace/docs.
    _, review_path = taxonomy_review_paths(root, document)
    if not review_path.is_file():
        raise ValueError(f"No saved DeepSeek taxonomy review at {review_path}. Run 'Review metadata with DeepSeek' first.")

    artifact = json.loads(review_path.read_text(encoding="utf-8"))
    if not isinstance(artifact, dict):
        raise ValueError("Saved review must be a JSON object")
    if artifact.get("errors"):
        raise ValueError("Saved review contains classification errors; resolve them before drafting a migration")
    results = artifact.get("results")
    if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
        raise ValueError("Expected exactly one document result in the saved Front Matter review")
    relative_document = document.relative_to(root).as_posix()
    if results[0].get("file") != relative_document:
        raise ValueError("Saved review belongs to a different document; rerun DeepSeek review")
    proposals = artifact.get("consolidated_proposals")
    if not isinstance(proposals, list):
        raise ValueError("Review has no valid consolidated_proposals array")
    if not proposals:
        print("No new taxonomy terms proposed. No migration needed; apply reviewed metadata directly.")
        return None

    taxonomy_path = root / "taxonomy" / "taxonomy.yml"
    if not taxonomy_path.is_file():
        raise ValueError(f"Canonical taxonomy not found: {taxonomy_path}")
    yaml = YAML(typ="safe")
    taxonomy = yaml.load(taxonomy_path.read_text(encoding="utf-8"))
    if not isinstance(taxonomy, dict) or not isinstance(taxonomy.get("dimensions"), dict):
        raise ValueError("Invalid canonical taxonomy structure")
    if taxonomy.get("version") != artifact.get("taxonomy_version"):
        raise ValueError("Review taxonomy version differs from canonical taxonomy; rerun review")
    dimensions = taxonomy["dimensions"]
    changes: dict[str, dict] = {}
    accepted = set()
    for proposal in proposals:
        if not isinstance(proposal, dict):
            raise ValueError("Malformed proposed term")
        dimension = proposal.get("dimension")
        term_id = proposal.get("id")
        if not isinstance(dimension, str) or dimension not in dimensions:
            raise ValueError(f"Unknown proposed taxonomy dimension: {dimension!r}")
        config = dimensions[dimension]
        if not config.get("ai_managed", False):
            raise ValueError(f"Dimension {dimension!r} does not allow AI-proposed additions")
        if not isinstance(term_id, str) or not ID.fullmatch(term_id):
            raise ValueError(f"Invalid proposed taxonomy ID: {term_id!r}")
        terms = config.get("terms")
        if not isinstance(terms, dict):
            raise ValueError(f"Malformed taxonomy dimension: {dimension}")
        if term_id in terms:
            print(f"Skipping already defined term: {dimension}.{term_id}")
            continue
        key = (dimension, term_id)
        if key in accepted:
            raise ValueError(f"Duplicate proposed term: {dimension}.{term_id}")
        accepted.add(key)
        label = proposal.get("label")
        description = proposal.get("description")
        if not isinstance(label, str) or not label.strip() or not isinstance(description, str) or not description.strip():
            raise ValueError(f"Missing label or description for {dimension}.{term_id}")
        if not isinstance(proposal.get("reason"), str) or not proposal["reason"].strip():
            raise ValueError(f"Missing proposal rationale for {dimension}.{term_id}")
        if not isinstance(proposal.get("evidence"), list) or not proposal["evidence"]:
            raise ValueError(f"Missing verified evidence for {dimension}.{term_id}")
        term = {"label": label.strip(), "description": description.strip()}
        kind = proposal.get("kind")
        if dimension == "technologies":
            kinds = taxonomy.get("technology_kinds", {})
            # taxonomy.py validates kinds during the migration dry run.
            if not isinstance(kind, str) or not ID.fullmatch(kind):
                raise ValueError(f"Technology proposal {term_id!r} has no valid kind")
            if isinstance(kinds, dict) and kinds and kind not in kinds:
                raise ValueError(f"Unrecognised technology kind {kind!r}")
            term["kind"] = kind
        elif kind is not None:
            raise ValueError(f"Non-technology proposal {dimension}.{term_id} cannot specify kind")
        parent = proposal.get("parent")
        if parent is not None:
            if not isinstance(parent, str) or not ID.fullmatch(parent):
                raise ValueError(f"Invalid parent for {dimension}.{term_id}")
            term["parent"] = parent
        aliases = proposal.get("aliases", [])
        if not isinstance(aliases, list) or any(not isinstance(a, str) or not a.strip() for a in aliases):
            raise ValueError(f"Invalid aliases for {dimension}.{term_id}")
        if len(aliases) != len(set(aliases)):
            raise ValueError(f"Duplicate aliases for {dimension}.{term_id}")
        if aliases:
            term["aliases"] = aliases
        changes.setdefault(dimension, {"add": {}})["add"][term_id] = term

    if not changes:
        print("All proposed terms already exist in the canonical taxonomy. No migration needed.")
        return None
    for dim, operations in changes.items():
        existing = dimensions[dim]["terms"]
        proposed = operations["add"]
        for term_id, term in proposed.items():
            parent = term.get("parent")
            if parent and parent not in existing and parent not in proposed:
                raise ValueError(f"Unknown parent {parent!r} for {dim}.{term_id}")

    # Use the review date as provenance; ensure a valid ISO date in the file name.
    date_text = artifact.get("introduced_date")
    try:
        date.fromisoformat(date_text)
    except (ValueError, TypeError):
        raise ValueError("Review has an invalid introduced_date") from None
    slug = document.stem.lower().replace("_", "-")
    slug = re.sub(r"[^a-z0-9-]+", "-", slug).strip("-")
    slug = re.sub(r"-+", "-", slug)
    migration_id = f"{date_text}-ai-{slug}"
    path = root / "taxonomy" / "migrations" / f"{migration_id}.yml"
    if path.exists():
        raise FileExistsError(f"Migration already exists: {path}; review it instead of overwriting")

    reasons = [f"{p['dimension']}.{p['id']}: {p['reason'].strip()}" for p in proposals
               if (p.get('dimension'), p.get('id')) in accepted]
    migration = {
        "schema_version": 2,
        "id": migration_id,
        "description": f"Review proposed taxonomy additions for {relative_document}.",
        "change_type": "vocabulary-expansion",
        "trigger": "content-driven",
        "governance": {
            "date": date_text,
            "source": "ai-proposed",
            "reason": "DeepSeek review of " + relative_document + ": " + " ".join(reasons),
        },
        "preconditions": {"taxonomy_version": taxonomy["version"]},
        "changes": changes,
    }
    # Check the actual repository's JSON schema before writing the draft.
    schema_path = root / "taxonomy" / "taxonomy-migration.schema.json"
    if not schema_path.is_file():
        raise ValueError(f"Cannot validate migration: missing {schema_path}")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(migration)
    path.parent.mkdir(parents=True, exist_ok=True)
    out_yaml = YAML()
    out_yaml.default_flow_style = False
    out_yaml.width = 100
    with path.open("x", encoding="utf-8") as out:
        out_yaml.dump(migration, out)
    print(f"Created REVIEW-ONLY taxonomy migration: {path.relative_to(root).as_posix()}")
    print(f"Review the YAML, then run: python scripts/taxonomy.py migrate {path.relative_to(root).as_posix()}")
    print("Only after approving it, rerun that command with --apply.")
    return path


def main() -> int:
    if len(sys.argv) < 3:
        print("ERROR: expected workspace and document paths", file=sys.stderr)
        return 2
    try:
        generate(Path(sys.argv[1]), Path(sys.argv[2]))
        return 0
    except (ValueError, OSError, json.JSONDecodeError, jsonschema.exceptions.ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
