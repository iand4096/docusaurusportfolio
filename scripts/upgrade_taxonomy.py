#!/usr/bin/env python3
"""Upgrade an existing taxonomy v1 to taxonomy v2 with typed technologies.

The upgrade is deliberately review-first:

  python scripts/upgrade_taxonomy.py

writes:

  taxonomy/taxonomy-v2-upgrade.md
  taxonomy/taxonomy-v2-upgrade.json

DeepSeek classifies each existing technology term as either:

- a genuine technology/method/technical technique, with one controlled `kind`;
- or an organisation/entity that does not belong in technologies.

The technology vocabulary is NOT intentionally reduced. A long career can and
should retain a large set of historical/current technologies where the terms
are genuine technical experience.

After reviewing the report:

  python scripts/upgrade_taxonomy.py --apply

updates taxonomy/taxonomy.yml to version 2. Genuine technologies receive a
`kind`. Organisation-like entries are marked deprecated instead of being deleted. Existing document front matter is NOT rewritten by this migration;
run taxonomy_ai.py afterwards to reclassify affected documents and review the
git diff.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests
from ruamel.yaml import YAML

import taxonomy as taxonomy_tools


API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_MD_REPORT = Path("taxonomy/taxonomy-v2-upgrade.md")
DEFAULT_JSON_REPORT = Path("taxonomy/taxonomy-v2-upgrade.json")

SYSTEM_PROMPT = r"""
You are auditing the technology dimension of a technical-writing/programming
portfolio taxonomy that represents roughly 25 years of professional experience.

Use British English. Return JSON only.

The goal is NOT to shrink the technology vocabulary. Historical and niche
technologies are valid when they represent genuine professional technical
experience.

For every supplied term, classify it as exactly one of:

- "technology": a real technology, software product, language, framework,
  library, standard, specification, protocol, developer/documentation tool,
  platform, infrastructure technology, technical modelling methodology,
  architecture style, or technical technique.
- "organisation": a company, employer, client, customer, consultancy,
  manufacturer, bank/financial institution, provider as a corporate entity, or
  other organisation that should not be a technology taxonomy value.

If classification is "technology", choose exactly one supplied TECHNOLOGY KIND.
If classification is "organisation", kind must be null.

Important examples:

- Python -> technology / programming-language
- Docusaurus -> technology / documentation-platform
- C4 model -> technology / modelling-methodology
- OCR -> technology / technical-technique
- REST -> technology / architecture-style
- Mastercard (corporation) -> organisation
- Morgan Stanley -> organisation
- Paysafe (company/provider) -> organisation
- STMicroelectronics (manufacturer) -> organisation
- Brightspot -> technology only when the supplied term description clearly
  refers to the CMS/software product rather than the company.

Do not classify a company as technology simply because it owns technology or
appears in technical project work.

Return exactly:

{
  "classifications": [
    {
      "id": "python",
      "classification": "technology",
      "kind": "programming-language",
      "reason": "The term is a programming language."
    },
    {
      "id": "mastercard",
      "classification": "organisation",
      "kind": null,
      "reason": "The supplied definition describes a financial-services corporation."
    }
  ]
}

Return exactly one classification for every supplied term ID and no extra IDs.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upgrade taxonomy v1 technologies to typed taxonomy v2")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=int, default=50, help="Technology terms per DeepSeek request")
    parser.add_argument("--max-tokens", type=int, default=12_000)
    parser.add_argument("--output", type=Path, default=DEFAULT_MD_REPORT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the reviewed v2 migration to taxonomy.yml; does not rewrite docs",
    )
    parser.add_argument(
        "--recheck-v2",
        action="store_true",
        help="Allow auditing an existing v2 taxonomy instead of requiring version 1",
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
                timeout=300,
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
                        "Return the audit again as one complete, strictly valid JSON object. "
                        "Include exactly one result for every supplied ID and no commentary."
                    ),
                }
            )
            time.sleep(2 ** (attempt - 1))
    raise RuntimeError(f"DeepSeek request failed after {attempts} attempts: {last_error}")


def load_raw_taxonomy(root: Path) -> dict[str, Any]:
    path = root / taxonomy_tools.TAXONOMY_PATH
    if not path.exists():
        raise ValueError(f"{path} does not exist")
    yaml = YAML(typ="safe")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.load(handle)
    if not isinstance(data, dict):
        raise ValueError("taxonomy.yml must contain a YAML object")
    return data


def active_v1_technology_terms(taxonomy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    dimensions = taxonomy.get("dimensions")
    if not isinstance(dimensions, dict) or not isinstance(dimensions.get("technologies"), dict):
        raise ValueError("taxonomy has no technologies dimension")
    terms = dimensions["technologies"].get("terms")
    if not isinstance(terms, dict):
        raise ValueError("technologies dimension has no terms")
    return {
        term_id: term
        for term_id, term in terms.items()
        if isinstance(term, dict) and term.get("governance", {}).get("status", "active") == "active"
    }


def batches(items: list[tuple[str, dict[str, Any]]], size: int) -> list[list[tuple[str, dict[str, Any]]]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def make_prompt(batch: list[tuple[str, dict[str, Any]]]) -> str:
    input_terms = []
    for term_id, term in batch:
        input_terms.append(
            {
                "id": term_id,
                "label": term.get("label"),
                "description": term.get("description"),
                "aliases": term.get("aliases", []),
                "existing_kind": term.get("kind"),
            }
        )
    return (
        "TECHNOLOGY KINDS:\n"
        + json.dumps(taxonomy_tools.DEFAULT_TECHNOLOGY_KINDS, indent=2, ensure_ascii=False)
        + "\n\nTERMS TO AUDIT:\n"
        + json.dumps(input_terms, indent=2, ensure_ascii=False)
    )


def validate_batch_result(
    result: dict[str, Any],
    expected_ids: set[str],
) -> list[dict[str, Any]]:
    raw = result.get("classifications")
    if not isinstance(raw, list):
        raise ValueError("response must contain classifications array")

    seen: set[str] = set()
    clean: list[dict[str, Any]] = []
    allowed_kinds = set(taxonomy_tools.DEFAULT_TECHNOLOGY_KINDS)
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("classification items must be objects")
        term_id = item.get("id")
        classification = item.get("classification")
        kind = item.get("kind")
        reason = item.get("reason")

        if term_id not in expected_ids:
            raise ValueError(f"unexpected classification ID {term_id!r}")
        if term_id in seen:
            raise ValueError(f"duplicate classification ID {term_id!r}")
        seen.add(term_id)
        if classification not in {"technology", "organisation"}:
            raise ValueError(f"{term_id}: invalid classification {classification!r}")
        if classification == "technology":
            if not isinstance(kind, str) or kind not in allowed_kinds:
                raise ValueError(f"{term_id}: technology classification requires an approved kind")
        elif kind is not None:
            raise ValueError(f"{term_id}: organisation classification must use kind: null")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"{term_id}: reason is required")

        clean.append(
            {
                "id": term_id,
                "classification": classification,
                "kind": kind,
                "reason": reason.strip(),
            }
        )

    missing = expected_ids - seen
    if missing:
        raise ValueError("missing classifications: " + ", ".join(sorted(missing)))
    return clean


def documents_referencing_terms(
    root: Path,
    term_ids: set[str],
) -> dict[str, list[str]]:
    references: dict[str, list[str]] = {term_id: [] for term_id in term_ids}
    if not term_ids:
        return references
    for path in taxonomy_tools.all_docs(root):
        try:
            front_matter, _ = taxonomy_tools.load_front_matter(path)
        except Exception:
            continue
        values = taxonomy_tools.value_as_list(front_matter.get("technologies", [])) or []
        for term_id in term_ids.intersection(values):
            references[term_id].append(path.relative_to(root).as_posix())
    return references


def render_report(
    classifications: list[dict[str, Any]],
    taxonomy: dict[str, Any],
    references: dict[str, list[str]],
    model: str,
) -> str:
    technologies = taxonomy["dimensions"]["technologies"]["terms"]
    valid = [item for item in classifications if item["classification"] == "technology"]
    organisations = [item for item in classifications if item["classification"] == "organisation"]

    lines = [
        "# Taxonomy v2 technology upgrade review",
        "",
        f"Model: `{model}`",
        "",
        "> Review this report before using `--apply`. The upgrade preserves genuine technical breadth and deprecates organisation-like terms rather than silently deleting them.",
        "",
        f"- Genuine technologies/methods: **{len(valid)}**",
        f"- Organisation/entity misclassifications: **{len(organisations)}**",
        "",
        "## Organisation/entity terms to remove from active technologies",
        "",
    ]

    if not organisations:
        lines.append("None detected.")
    else:
        for item in sorted(organisations, key=lambda value: value["id"]):
            term = technologies[item["id"]]
            lines.extend(
                [
                    f"### `{item['id']}` — {term.get('label', item['id'])}",
                    "",
                    f"Current description: {term.get('description', '')}",
                    "",
                    f"Reason: {item['reason']}",
                    "",
                ]
            )
            refs = references.get(item["id"], [])
            if refs:
                lines.append("Referenced by:")
                lines.extend(f"- `{path}`" for path in refs)
                lines.append("")

    lines.extend(["## Technology kinds", ""])
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in valid:
        grouped.setdefault(item["kind"], []).append(item)
    for kind_id in sorted(grouped):
        kind_label = taxonomy_tools.DEFAULT_TECHNOLOGY_KINDS[kind_id]["label"]
        lines.extend([f"### {kind_label} (`{kind_id}`)", ""])
        for item in sorted(grouped[kind_id], key=lambda value: value["id"]):
            label = technologies[item["id"]].get("label", item["id"])
            lines.append(f"- `{item['id']}` — {label}: {item['reason']}")
        lines.append("")

    lines.extend(
        [
            "## Suggested migration sequence",
            "",
            "1. Review the classifications above.",
            "2. Run `python scripts/upgrade_taxonomy.py --apply`.",
            "3. Review `git diff` for taxonomy and generated tag changes.",
            "4. Run `python scripts/taxonomy_ai.py --all` to see document reclassification suggestions.",
            "5. Apply/review those metadata changes, then run `python scripts/taxonomy.py check --all`.",
            "",
        ]
    )
    return "\n".join(lines)


def write_taxonomy(path: Path, taxonomy: dict[str, Any]) -> None:
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 100
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# Canonical controlled vocabulary for portfolio metadata.\n")
        handle.write("# AI may propose changes, but only reviewed repository changes adopt them.\n\n")
        yaml.dump(taxonomy, handle)


def apply_upgrade(
    root: Path,
    taxonomy: dict[str, Any],
    classifications: list[dict[str, Any]],
) -> None:
    taxonomy["version"] = taxonomy_tools.TAXONOMY_VERSION
    taxonomy["technology_kinds"] = json.loads(
        json.dumps(taxonomy_tools.DEFAULT_TECHNOLOGY_KINDS)
    )

    dimensions = taxonomy["dimensions"]
    technologies = dimensions["technologies"]
    content_type_ids = set(dimensions["content_types"]["terms"])
    constraints = {
        type_id: dict(limits)
        for type_id, limits in taxonomy_tools.DEFAULT_TECHNOLOGY_CONSTRAINTS_BY_TYPE.items()
        if type_id in content_type_ids
    }
    if constraints:
        existing = technologies.get("constraints_by_type", {})
        if not isinstance(existing, dict):
            existing = {}
        technologies["constraints_by_type"] = {**constraints, **existing}

    by_id = {item["id"]: item for item in classifications}
    for term_id, term in technologies["terms"].items():
        if term.get("governance", {}).get("status") != "active":
            continue
        classification = by_id.get(term_id)
        if classification is None:
            raise ValueError(f"no classification for active technology {term_id!r}")

        if classification["classification"] == "technology":
            term["kind"] = classification["kind"]
        else:
            term.pop("kind", None)
            governance = term["governance"]
            governance["status"] = "deprecated"
            governance.pop("replaced_by", None)
            governance["deprecation_reason"] = (
                "Removed from active technologies during taxonomy v2 entity-type audit: "
                + classification["reason"]
            )

    taxonomy_tools.validate_taxonomy_schema(taxonomy, root / taxonomy_tools.SCHEMA_PATH)
    taxonomy_tools.validate_taxonomy_semantics(taxonomy)
    write_taxonomy(root / taxonomy_tools.TAXONOMY_PATH, taxonomy)
    taxonomy_tools.generate_derived_files(root, taxonomy)


def main() -> int:
    args = parse_args()
    root = args.root.resolve()

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("ERROR: DEEPSEEK_API_KEY is not set", file=sys.stderr)
        return 2

    try:
        taxonomy = load_raw_taxonomy(root)
        version = taxonomy.get("version")
        if version != 1 and not (args.recheck_v2 and version == taxonomy_tools.TAXONOMY_VERSION):
            raise ValueError(
                f"expected taxonomy version 1; found {version!r}. "
                "Use --recheck-v2 to audit an existing v2 taxonomy."
            )
        terms = active_v1_technology_terms(taxonomy)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    items = sorted(terms.items())
    if not items:
        print("ERROR: no active technology terms found", file=sys.stderr)
        return 1

    classifications: list[dict[str, Any]] = []
    term_batches = batches(items, args.batch_size)
    for index, batch in enumerate(term_batches, start=1):
        print(f"auditing technology batch {index}/{len(term_batches)} ({len(batch)} terms)")
        expected = {term_id for term_id, _ in batch}
        try:
            raw = request_json(
                api_key,
                args.model,
                make_prompt(batch),
                args.max_tokens,
            )
            classifications.extend(validate_batch_result(raw, expected))
        except Exception as error:
            print(f"ERROR: batch {index}: {error}", file=sys.stderr)
            return 1

    by_id = {item["id"]: item for item in classifications}
    if set(by_id) != set(terms):
        print("ERROR: audit did not classify every active technology", file=sys.stderr)
        return 1

    organisation_ids = {
        item["id"] for item in classifications if item["classification"] == "organisation"
    }
    references = documents_referencing_terms(root, organisation_ids)

    md_output = args.output if args.output.is_absolute() else root / args.output
    json_output = args.json_output if args.json_output.is_absolute() else root / args.json_output
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.write_text(render_report(classifications, taxonomy, references, args.model), encoding="utf-8")
    json_output.write_text(
        json.dumps(
            {
                "source_taxonomy_version": taxonomy.get("version"),
                "target_taxonomy_version": taxonomy_tools.TAXONOMY_VERSION,
                "model": args.model,
                "technology_kinds": taxonomy_tools.DEFAULT_TECHNOLOGY_KINDS,
                "classifications": classifications,
                "organisation_references": references,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {md_output.relative_to(root).as_posix()}")
    print(f"wrote {json_output.relative_to(root).as_posix()}")

    if args.apply:
        try:
            apply_upgrade(root, taxonomy, classifications)
        except Exception as error:
            print(f"ERROR: failed to apply upgrade: {error}", file=sys.stderr)
            return 1
        print("applied taxonomy v2 migration; review `git diff` before reclassifying documents")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
