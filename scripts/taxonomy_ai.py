#!/usr/bin/env python3
"""DeepSeek-assisted metadata classification and taxonomy-gap suggestions.

AI output is advisory by default. It never controls deterministic CI success.

Taxonomy v2 understands technology subclasses (`kind`) and a long-career
portfolio model: the technology vocabulary may be broad, while each individual
page is kept selective through global and content-type-specific cardinality.

Examples:

  python scripts/taxonomy_ai.py docs/skills/APIDocumentation.md
  python scripts/taxonomy_ai.py --changed-base origin/main
  python scripts/taxonomy_ai.py --all --apply

When --apply is used, proposed terms are added to taxonomy/taxonomy.yml with
`source: ai-proposed`, metadata is written to document front matter, and
derived Docusaurus/Front Matter files are regenerated. Nothing is committed or
pushed; the git diff remains the human approval surface.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

import requests
from ruamel.yaml import YAML

import taxonomy as taxonomy_tools


API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_MARKDOWN_REPORT = Path("taxonomy/taxonomy-ai-suggestions.md")
DEFAULT_JSON_REPORT = Path("taxonomy/taxonomy-ai-suggestions.json")
TERM_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

SYSTEM_PROMPT = r"""
You classify content against a repository-controlled taxonomy for a Docusaurus
portfolio representing roughly 25 years of technical writing, programming,
documentation engineering, APIs and software tooling. You may also identify
genuine gaps in the controlled vocabulary.

Use British English. Return JSON only.

CORE RULES:

- Existing taxonomy values are preferred whenever they adequately represent the
  document.
- Select only values materially supported by the supplied document.
- Prefer precise metadata over indiscriminate tagging.
- Respect global and content-type-specific cardinality constraints.
- For an existing term, return its exact ID.
- Never silently invent an ID and use it as an existing term.
- Lifecycle is policy-controlled: choose an existing lifecycle value and never
  propose a lifecycle term.
- A new term may be proposed only in a dimension marked ai_managed=true.

TECHNOLOGY POLICY:

- The technology vocabulary is intentionally broad because the portfolio spans
  a long career. Do not remove or avoid a legitimate technology merely because
  it is historical or appears in only one document.
- A technology must be materially used, documented, implemented, tested,
  explained or demonstrated by the page.
- Every technology term has a controlled `kind`. New technology proposals MUST
  use one of the supplied technology kind IDs.
- Companies, employers, clients, customers, consultancies, manufacturers,
  banks/financial institutions and other corporate organisations are NOT
  technologies.
- Do not classify a company name as a technology simply because technical work
  was performed for that company.
- A software product/platform sharing a company/brand name can be a technology
  only when the document is materially about using that product/platform.
- Reusable technical methods are allowed when an existing kind such as
  modelling-methodology, architecture-style or technical-technique applies.

TAXONOMY EXPANSION HAS A HIGH BAR. Propose a new term only when:

1. The concept is substantively present in this document.
2. No existing term accurately represents it.
3. The concept is reusable and is reasonably likely to classify other content,
   OR it is significant evidence of genuine professional technology experience.
4. It is meaningfully distinct from existing terms and aliases.
5. It is not merely a project/client/employer/company name or passing mention.

For every proposed term provide a concise rationale and one or more short exact
source excerpts as evidence. Evidence must occur verbatim in DOCUMENT CONTENT.
Use a stable lower-case kebab-case ID. A parent is optional and must refer to an
existing or simultaneously proposed term in the same dimension.

Return exactly this top-level JSON shape:

{
  "metadata": {
    "type": "case-study",
    "audiences": ["developers"],
    "topics": ["api-documentation"],
    "technologies": ["openapi"],
    "lifecycle": "current"
  },
  "selection_reasons": {
    "type": "Concise evidence-based rationale.",
    "audiences": "Concise evidence-based rationale.",
    "topics": "Concise evidence-based rationale.",
    "technologies": "Concise evidence-based rationale.",
    "lifecycle": "Concise evidence-based rationale."
  },
  "proposed_taxonomy_terms": [
    {
      "dimension": "technologies",
      "id": "new-tool",
      "label": "New Tool",
      "description": "A reusable technical tool.",
      "kind": "developer-tool",
      "parent": null,
      "aliases": [],
      "reason": "Why the existing vocabulary is insufficient and this is genuine technical experience.",
      "evidence": ["exact excerpt from the document"]
    }
  ]
}

For proposals outside the technologies dimension, omit `kind`. Use an empty
proposed_taxonomy_terms array when the existing taxonomy is sufficient. Do not
include Markdown fences or commentary.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Suggest or apply taxonomy metadata with DeepSeek")
    parser.add_argument("paths", nargs="*", help="docs Markdown/MDX files or directories")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    parser.add_argument("--all", action="store_true", help="Review every docs/**/*.md[x] file")
    parser.add_argument("--changed-base", help="Review docs changed since this git SHA")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-file-chars", type=int, default=120_000)
    parser.add_argument("--max-tokens", type=int, default=8_000)
    parser.add_argument("--output", type=Path, default=DEFAULT_MARKDOWN_REPORT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument(
        "--introduced-date",
        default=date.today().isoformat(),
        help="Introduction date for applied AI-proposed taxonomy terms",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply suggestions to the working tree; review and commit the diff manually",
    )
    return parser.parse_args()


def parse_model_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if not text:
        raise ValueError("DeepSeek returned empty content")
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("DeepSeek response must be a JSON object")
    return parsed


def request_json(
    api_key: str,
    model: str,
    user_prompt: str,
    max_tokens: int,
    attempts: int = 3,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "thinking": {"type": "disabled"},
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = requests.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=240,
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise ValueError("DeepSeek response has no string message.content")
            return parse_model_json(content)
        except (requests.RequestException, json.JSONDecodeError, KeyError, IndexError, ValueError) as error:
            last_error = error
            if attempt == attempts:
                break
            payload["messages"].append(
                {
                    "role": "user",
                    "content": (
                        "Return the classification again as one complete, strictly valid JSON object "
                        "matching the required schema. Do not return empty content or Markdown fences."
                    ),
                }
            )
            time.sleep(2 ** (attempt - 1))
    raise RuntimeError(f"DeepSeek request failed after {attempts} attempts: {last_error}")


def taxonomy_for_prompt(taxonomy: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "technology_kinds": taxonomy["technology_kinds"],
        "dimensions": {},
    }
    for dimension_id, dimension in taxonomy["dimensions"].items():
        terms = {}
        for term_id, term in dimension["terms"].items():
            if term["governance"]["status"] != "active":
                continue
            entry = {
                "label": term["label"],
                "description": term["description"],
                "parent": term.get("parent"),
                "aliases": term.get("aliases", []),
            }
            if dimension_id == "technologies":
                entry["kind"] = term["kind"]
            terms[term_id] = entry
        result["dimensions"][dimension_id] = {
            "description": dimension["description"],
            "metadata_field": dimension["metadata_field"],
            "required": dimension["required"],
            "multiple": dimension["multiple"],
            "min": dimension["min"],
            "max": dimension["max"],
            "constraints_by_type": dimension.get("constraints_by_type", {}),
            "ai_managed": dimension["ai_managed"],
            "terms": terms,
        }
    return result


def plain_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): plain_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [plain_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def document_payload(path: Path, root: Path, max_chars: int) -> tuple[dict[str, Any], str]:
    front_matter, body = taxonomy_tools.load_front_matter(path)
    dimensions = taxonomy_tools.load_and_validate_taxonomy(root)["dimensions"]
    current = {}
    for dimension in dimensions.values():
        field = dimension["metadata_field"]
        if field in front_matter:
            current[field] = plain_value(front_matter[field])
    if "tags" in front_matter:
        current["tags"] = plain_value(front_matter["tags"])
    if len(body) > max_chars:
        body = body[:max_chars] + "\n\n[CONTENT TRUNCATED FOR AI CLASSIFICATION]"
    return current, body


def clean_string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return list(value)


def active_term_ids(dimension: dict[str, Any]) -> set[str]:
    return set(taxonomy_tools.active_terms(dimension))


def validate_ai_result(
    result: dict[str, Any],
    taxonomy: dict[str, Any],
    document_text: str,
) -> dict[str, Any]:
    metadata = result.get("metadata")
    reasons = result.get("selection_reasons")
    raw_proposals = result.get("proposed_taxonomy_terms")
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")
    if not isinstance(reasons, dict):
        raise ValueError("selection_reasons must be an object")
    if not isinstance(raw_proposals, list):
        raise ValueError("proposed_taxonomy_terms must be an array")

    dimensions = taxonomy["dimensions"]
    kind_ids = set(taxonomy["technology_kinds"])
    proposals: list[dict[str, Any]] = []
    proposed_ids: dict[str, set[str]] = {dimension_id: set() for dimension_id in dimensions}

    for raw in raw_proposals:
        if not isinstance(raw, dict):
            raise ValueError("each proposed taxonomy term must be an object")
        dimension_id = raw.get("dimension")
        term_id = raw.get("id")
        label = raw.get("label")
        description = raw.get("description")
        kind = raw.get("kind")
        parent = raw.get("parent")
        aliases = raw.get("aliases", [])
        reason = raw.get("reason")
        evidence = raw.get("evidence")

        if dimension_id not in dimensions:
            raise ValueError(f"proposal uses unknown dimension {dimension_id!r}")
        dimension = dimensions[dimension_id]
        if not dimension["ai_managed"]:
            raise ValueError(f"AI may not propose terms in {dimension_id!r}")
        if not isinstance(term_id, str) or not TERM_ID_RE.fullmatch(term_id):
            raise ValueError(f"invalid proposed term ID {term_id!r}")
        if term_id in dimension["terms"]:
            raise ValueError(f"proposed term {dimension_id}.{term_id} already exists")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"proposal {dimension_id}.{term_id} needs a label")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"proposal {dimension_id}.{term_id} needs a description")

        if dimension_id == "technologies":
            if not isinstance(kind, str) or kind not in kind_ids:
                raise ValueError(
                    f"technology proposal {term_id!r} must use one approved technology kind"
                )
            signals = [
                name
                for name, pattern in taxonomy_tools.ORGANISATION_LIKE_DESCRIPTION_PATTERNS
                if pattern.search(description)
            ]
            if signals:
                raise ValueError(
                    f"technology proposal {term_id!r} looks organisation-like "
                    f"({', '.join(signals)}); do not create company/employer/client technologies"
                )
        elif kind is not None:
            raise ValueError(f"proposal {dimension_id}.{term_id} must not contain kind")

        if parent is not None and not isinstance(parent, str):
            raise ValueError(f"proposal {dimension_id}.{term_id} has invalid parent")
        if not isinstance(aliases, list) or not all(isinstance(item, str) for item in aliases):
            raise ValueError(f"proposal {dimension_id}.{term_id} aliases must be strings")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"proposal {dimension_id}.{term_id} needs a reason")
        if not isinstance(evidence, list) or not evidence or not all(
            isinstance(item, str) and item.strip() for item in evidence
        ):
            raise ValueError(f"proposal {dimension_id}.{term_id} needs evidence")
        for excerpt in evidence:
            if excerpt not in document_text:
                raise ValueError(
                    f"proposal {dimension_id}.{term_id} evidence is not an exact document excerpt"
                )

        label_cf = label.strip().casefold()
        existing_names = {term["label"].strip().casefold() for term in dimension["terms"].values()}
        existing_names.update(
            alias.strip().casefold()
            for term in dimension["terms"].values()
            for alias in term.get("aliases", [])
        )
        if label_cf in existing_names:
            raise ValueError(
                f"proposal {dimension_id}.{term_id} duplicates an existing label or alias"
            )

        proposal: dict[str, Any] = {
            "dimension": dimension_id,
            "id": term_id,
            "label": label.strip(),
            "description": description.strip(),
            "parent": parent,
            "aliases": sorted(
                {
                    item.strip()
                    for item in aliases
                    if item.strip() and item.strip().casefold() != label_cf
                },
                key=str.casefold,
            ),
            "reason": reason.strip(),
            "evidence": [item.strip() for item in evidence],
        }
        if dimension_id == "technologies":
            proposal["kind"] = kind
        proposals.append(proposal)
        proposed_ids[dimension_id].add(term_id)

    for proposal in proposals:
        parent = proposal.get("parent")
        if not parent:
            continue
        dimension_id = proposal["dimension"]
        if parent not in dimensions[dimension_id]["terms"] and parent not in proposed_ids[dimension_id]:
            raise ValueError(
                f"proposal {dimension_id}.{proposal['id']} uses unknown parent {parent!r}"
            )

    # Validate type first because other dimensions may use content-type-specific limits.
    type_dimension = dimensions["content_types"]
    type_field = type_dimension["metadata_field"]
    type_value = metadata.get(type_field)
    if not isinstance(type_value, str):
        raise ValueError(f"metadata.{type_field} must be a single ID")
    allowed_types = active_term_ids(type_dimension) | proposed_ids["content_types"]
    if type_value not in allowed_types:
        raise ValueError(f"metadata.{type_field} uses undeclared ID {type_value!r}")

    clean_metadata: dict[str, Any] = {}
    for dimension_id, dimension in dimensions.items():
        field = dimension["metadata_field"]
        value = metadata.get(field)

        if dimension["multiple"]:
            values = clean_string_list(value)
            if values is None:
                raise ValueError(f"metadata.{field} must be an array of IDs")
        else:
            if not isinstance(value, str):
                raise ValueError(f"metadata.{field} must be a single ID")
            values = [value]

        minimum, maximum = taxonomy_tools.effective_limits(dimension, type_value)
        if len(values) < minimum or len(values) > maximum:
            raise ValueError(
                f"metadata.{field} violates cardinality {minimum}..{maximum} "
                f"for content type {type_value!r}"
            )
        if len(values) != len(set(values)):
            raise ValueError(f"metadata.{field} contains duplicate IDs")

        allowed = active_term_ids(dimension) | proposed_ids[dimension_id]
        unknown = [term_id for term_id in values if term_id not in allowed]
        if unknown:
            raise ValueError(f"metadata.{field} uses undeclared IDs: {unknown!r}")

        clean_metadata[field] = values if dimension["multiple"] else values[0]
        reason = reasons.get(field)
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"selection_reasons.{field} must be a concise string")

    return {
        "metadata": clean_metadata,
        "selection_reasons": {field: reasons[field].strip() for field in clean_metadata},
        "proposed_taxonomy_terms": proposals,
    }


def make_user_prompt(
    path: Path,
    root: Path,
    taxonomy: dict[str, Any],
    current: dict[str, Any],
    body: str,
) -> str:
    return (
        "Classify this document using the controlled taxonomy below. Return JSON only.\n\n"
        "CONTROLLED TAXONOMY:\n"
        + json.dumps(taxonomy_for_prompt(taxonomy), indent=2, ensure_ascii=False)
        + "\n\nFILE: "
        + path.relative_to(root).as_posix()
        + "\nCURRENT TAXONOMY FRONT MATTER:\n"
        + json.dumps(current, indent=2, ensure_ascii=False)
        + "\n\nDOCUMENT CONTENT:\n"
        + body
    )


def merge_global_proposals(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for result in results:
        file_path = result["file"]
        for proposal in result["proposed_taxonomy_terms"]:
            key = (proposal["dimension"], proposal["id"])
            existing = merged.get(key)
            proposal_with_files = dict(proposal)
            proposal_with_files["proposed_by_files"] = [file_path]
            if existing is None:
                merged[key] = proposal_with_files
                continue

            comparable_keys = ["label", "description", "kind", "parent", "aliases"]
            if any(existing.get(name) != proposal.get(name) for name in comparable_keys):
                raise ValueError(f"conflicting AI proposals for {key[0]}.{key[1]} across documents")
            existing["proposed_by_files"].append(file_path)
            existing["evidence"] = list(dict.fromkeys(existing["evidence"] + proposal["evidence"]))
            if proposal["reason"] not in existing["reason"]:
                existing["reason"] += " " + proposal["reason"]
    return [merged[key] for key in sorted(merged)]


def yaml_snippet_for_proposal(proposal: dict[str, Any]) -> str:
    term: dict[str, Any] = {
        "label": proposal["label"],
        "description": proposal["description"],
    }
    if proposal.get("kind"):
        term["kind"] = proposal["kind"]
    if proposal.get("parent"):
        term["parent"] = proposal["parent"]
    if proposal.get("aliases"):
        term["aliases"] = proposal["aliases"]
    yaml = YAML()
    yaml.default_flow_style = False
    stream = io.StringIO()
    yaml.dump({proposal["id"]: term}, stream)
    return stream.getvalue().rstrip()


def render_markdown_report(
    results: list[dict[str, Any]],
    proposals: list[dict[str, Any]],
    model: str,
) -> str:
    lines = [
        "# Taxonomy AI suggestions",
        "",
        f"Model: `{model}`",
        "",
        "> Advisory only. Repository taxonomy and deterministic validation remain authoritative.",
        "",
    ]
    if not results:
        lines.extend(["No documentation files required AI classification.", ""])
        return "\n".join(lines)

    for result in results:
        lines.extend([f"## `{result['file']}`", "", "### Suggested metadata", "", "```yaml"])
        yaml = YAML()
        yaml.default_flow_style = False
        stream = io.StringIO()
        yaml.dump(result["metadata"], stream)
        lines.extend([stream.getvalue().rstrip(), "```", "", "### Rationale", ""])
        for field, reason in result["selection_reasons"].items():
            lines.append(f"- **{field}**: {reason}")
        lines.append("")

        file_proposals = result["proposed_taxonomy_terms"]
        if file_proposals:
            lines.extend(["### Taxonomy expansion proposals", ""])
            for proposal in file_proposals:
                kind_suffix = f" — kind `{proposal['kind']}`" if proposal.get("kind") else ""
                lines.extend(
                    [
                        f"#### `{proposal['dimension']}.{proposal['id']}` — {proposal['label']}{kind_suffix}",
                        "",
                        proposal["reason"],
                        "",
                        "Suggested term definition:",
                        "",
                        "```yaml",
                        yaml_snippet_for_proposal(proposal),
                        "```",
                        "",
                        "Evidence:",
                    ]
                )
                for excerpt in proposal["evidence"]:
                    lines.append(f"- `{excerpt}`")
                lines.append("")

    if proposals:
        lines.extend(["# Consolidated taxonomy proposals", ""])
        for proposal in proposals:
            files = ", ".join(f"`{item}`" for item in proposal["proposed_by_files"])
            lines.extend(
                [
                    f"## `{proposal['dimension']}.{proposal['id']}`",
                    "",
                    f"Suggested from: {files}",
                    "",
                    "```yaml",
                    yaml_snippet_for_proposal(proposal),
                    "```",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def write_taxonomy(path: Path, taxonomy: dict[str, Any]) -> None:
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 100
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# Canonical controlled vocabulary for portfolio metadata.\n")
        handle.write("# AI may propose changes, but only reviewed repository changes adopt them.\n\n")
        yaml.dump(taxonomy, handle)


def apply_results(
    root: Path,
    taxonomy: dict[str, Any],
    results: list[dict[str, Any]],
    proposals: list[dict[str, Any]],
    introduced: str,
) -> None:
    review = taxonomy["governance"]["default_review"]

    for proposal in proposals:
        dimension = taxonomy["dimensions"][proposal["dimension"]]
        term_id = proposal["id"]
        if term_id in dimension["terms"]:
            continue
        term: dict[str, Any] = {
            "label": proposal["label"],
            "description": proposal["description"],
        }
        if proposal.get("kind"):
            term["kind"] = proposal["kind"]
        if proposal.get("parent"):
            term["parent"] = proposal["parent"]
        if proposal.get("aliases"):
            term["aliases"] = proposal["aliases"]
        term["governance"] = {
            "status": "active",
            "introduced": introduced,
            "source": "ai-proposed",
            "review": review,
        }
        dimension["terms"][term_id] = term

    taxonomy_tools.validate_taxonomy_schema(taxonomy, root / taxonomy_tools.SCHEMA_PATH)
    taxonomy_tools.validate_taxonomy_semantics(taxonomy)
    write_taxonomy(root / taxonomy_tools.TAXONOMY_PATH, taxonomy)

    for result in results:
        path = root / result["file"]
        front_matter, body = taxonomy_tools.load_front_matter(path)
        for dimension in taxonomy["dimensions"].values():
            field = dimension["metadata_field"]
            value = result["metadata"][field]
            if dimension["required"] or value not in ([], "", None):
                front_matter[field] = value
            elif field in front_matter:
                del front_matter[field]
        taxonomy_tools.write_front_matter(path, front_matter, body)
        taxonomy_tools.sync_document_tags(path, taxonomy)
        print(f"applied metadata to {result['file']}")

    taxonomy_tools.generate_derived_files(root, taxonomy)

    errors: list[str] = []
    errors.extend(taxonomy_tools.check_derived_files(root, taxonomy))
    for result in results:
        errors.extend(
            taxonomy_tools.validate_document_front_matter(root / result["file"], root, taxonomy)
        )
    if errors:
        raise ValueError("applied changes failed deterministic validation:\n" + "\n".join(errors))


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.introduced_date):
        print("ERROR: --introduced-date must be YYYY-MM-DD", file=sys.stderr)
        return 2

    modes = int(bool(args.paths)) + int(bool(args.all)) + int(bool(args.changed_base))
    if modes != 1:
        print("ERROR: choose exactly one of explicit paths, --all, or --changed-base", file=sys.stderr)
        return 2

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("ERROR: DEEPSEEK_API_KEY is not set", file=sys.stderr)
        return 2

    try:
        taxonomy = taxonomy_tools.load_and_validate_taxonomy(root)
        docs = taxonomy_tools.select_docs(
            root,
            explicit_paths=args.paths,
            all_files=args.all,
            changed_base=args.changed_base,
        )
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for index, path in enumerate(docs, start=1):
        relative = path.relative_to(root).as_posix()
        print(f"classifying {index}/{len(docs)}: {relative}")
        try:
            current, body = document_payload(path, root, args.max_file_chars)
            raw = request_json(
                api_key,
                args.model,
                make_user_prompt(path, root, taxonomy, current, body),
                args.max_tokens,
            )
            validated = validate_ai_result(raw, taxonomy, body)
            validated["file"] = relative
            validated["current_metadata"] = current
            results.append(validated)
        except Exception as error:
            errors.append({"file": relative, "error": str(error)})
            print(f"WARNING: {relative}: {error}", file=sys.stderr)

    try:
        proposals = merge_global_proposals(results)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    markdown_report = render_markdown_report(results, proposals, args.model)
    output = args.output if args.output.is_absolute() else root / args.output
    json_output = args.json_output if args.json_output.is_absolute() else root / args.json_output
    output.parent.mkdir(parents=True, exist_ok=True)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown_report, encoding="utf-8")
    json_output.write_text(
        json.dumps(
            {
                "taxonomy_version": taxonomy_tools.TAXONOMY_VERSION,
                "model": args.model,
                "results": results,
                "consolidated_proposals": proposals,
                "errors": errors,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {output.relative_to(root).as_posix()}")
    print(f"wrote {json_output.relative_to(root).as_posix()}")

    if args.apply:
        if errors:
            print(
                "ERROR: refusing --apply because one or more documents failed AI classification",
                file=sys.stderr,
            )
            return 1
        try:
            apply_results(root, taxonomy, results, proposals, args.introduced_date)
        except Exception as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print("AI suggestions applied to the working tree. Review `git diff` before committing.")

    # AI operational failures remain advisory in CI when this step is configured
    # with continue-on-error / non-blocking workflow semantics.
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
