#!/usr/bin/env python3
"""Create the initial v2 controlled taxonomy from repository Markdown/MDX.

This bootstrap command reads the eligible content corpus and uses DeepSeek in
two passes:

1. Batch-level concept discovery with evidence.
2. Site-wide consolidation/deduplication.

Taxonomy v2 deliberately preserves the breadth expected in a long technical
career. Technology terms are not pruned merely because only one page provides
evidence, provided that page materially demonstrates or documents the
technology. Every technology receives a controlled `kind` such as
`programming-language`, `documentation-platform`, or `modelling-methodology`.
Companies/employers/clients are explicitly excluded from technologies.

Outputs:

  taxonomy/taxonomy.yml
  taxonomy/taxonomy-generation.json
  docs/tags.yml
  .frontmatter/generated-taxonomy.json

The script does NOT modify document front matter. Review the generated taxonomy
before running taxonomy_ai.py.
"""

from __future__ import annotations

import argparse
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
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_OUTPUT = Path("taxonomy/taxonomy.yml")
DEFAULT_AUDIT_OUTPUT = Path("taxonomy/taxonomy-generation.json")
MARKDOWN_SUFFIXES = {".md", ".mdx"}
TERM_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

EXCLUDED_DIRS = {
    ".git",
    ".docusaurus",
    ".frontmatter",
    ".idea",
    ".pytest_cache",
    ".venv",
    ".vscode",
    "build",
    "dist",
    "node_modules",
    "static",
    "taxonomy",
    "venv",
}

DISCOVERED_DIMENSIONS: dict[str, dict[str, Any]] = {
    "content_types": {
        "description": "The structural or editorial type of the content.",
        "metadata_field": "type",
        "required": True,
        "multiple": False,
        "min": 1,
        "max": 1,
        "docusaurus_tags": False,
        "ai_managed": True,
    },
    "audiences": {
        "description": "Audiences for whom the content is materially relevant.",
        "metadata_field": "audiences",
        "required": True,
        "multiple": True,
        "min": 1,
        "max": 3,
        "docusaurus_tags": False,
        "ai_managed": True,
    },
    "topics": {
        "description": "Reusable subject areas substantially covered by the content.",
        "metadata_field": "topics",
        "required": True,
        "multiple": True,
        "min": 1,
        "max": 5,
        "docusaurus_tags": True,
        "ai_managed": True,
    },
    "technologies": {
        "description": (
            "Technologies, standards, tools, platforms, technical methods and techniques "
            "materially used, documented or demonstrated."
        ),
        "metadata_field": "technologies",
        "required": False,
        "multiple": True,
        "min": 0,
        # Global ceiling for broad overview pages. More selective per-content-type
        # limits are added when the corresponding content types exist.
        "max": 50,
        "docusaurus_tags": True,
        "ai_managed": True,
    },
}

LIFECYCLE_DIMENSION = {
    "description": "The publication lifecycle state of the content.",
    "metadata_field": "lifecycle",
    "required": True,
    "multiple": False,
    "min": 1,
    "max": 1,
    "docusaurus_tags": False,
    "ai_managed": False,
    "terms": {
        "current": {
            "label": "Current",
            "description": "Content that represents current practice, capability or portfolio material.",
        },
        "historical": {
            "label": "Historical",
            "description": "Content intentionally retained as a historical example or past project.",
        },
        "archived": {
            "label": "Archived",
            "description": "Content retained for record purposes but no longer treated as active portfolio material.",
        },
    },
}

EXTRACTION_SYSTEM_PROMPT = r"""
You are performing concept discovery for a repository-controlled metadata
 taxonomy used by a Docusaurus portfolio representing roughly 25 years of
 technical writing, programming, documentation engineering, software tooling,
 API work and systems experience.

Use British English. Return JSON only.

Discover candidates for exactly four dimensions:

- content_types: structural/editorial page types represented by the corpus.
- audiences: groups for whom the content is materially relevant.
- topics: reusable subject areas substantially discussed by the content.
- technologies: actual technologies, standards, specifications, protocols,
  languages, frameworks, libraries, tools, platforms, technical methods,
  modelling approaches, architecture styles or technical techniques materially
  used, documented, explained or demonstrated.

IMPORTANT TECHNOLOGY POLICY:

- This is a long-career portfolio. Do NOT optimise the technology vocabulary for
  small size.
- A technology may be retained even when currently evidenced by only one page
  if the page materially demonstrates or documents genuine professional use.
- Historical technologies are valid portfolio evidence.
- Every technology candidate MUST use one of the supplied TECHNOLOGY KINDS.
- Companies, employers, clients, customers, consultancies, manufacturers,
  financial institutions and other corporate organisations are NEVER
  technologies merely because they appear in technical project content.
- A product/platform may be a technology when the evidence is about using the
  product itself, not merely working for or with the company that owns it.
- Example: Docusaurus -> technology; Mastercard -> organisation, not technology.
- Example: Brightspot CMS -> technology when the content discusses the CMS;
  Brightspot as an employer/vendor -> not a technology.
- Example: C4 model -> modelling-methodology is allowed.
- Example: OCR -> technical-technique is allowed when OCR itself is materially
  demonstrated.
- Example: REST -> architecture-style is allowed.

GENERAL RULES:

- Base every candidate on supplied repository content.
- Do not create one term per noun or heading.
- Do not create near-duplicate synonyms.
- Do not use navigation boilerplate as evidence.
- Do not classify passing mentions as substantive topics or technologies.
- Do not infer unsupported audiences.
- Do not use the portfolio author's name as taxonomy metadata.
- Do not use employer/client/project names as topics unless they genuinely
  represent a reusable subject domain (for example `payments`).
- IDs must be stable lower-case kebab-case identifiers.
- Evidence FILE values must exactly match supplied FILE values.
- Keep evidence reasons concise.
- Do not create lifecycle values; lifecycle is governed separately.

Return JSON with exactly this top-level shape:

{
  "candidates": {
    "content_types": [
      {
        "id": "case-study",
        "label": "Case study",
        "description": "A documented example of work, approach and outcomes.",
        "parent": null,
        "aliases": [],
        "evidence": [
          {"file": "docs/example.md", "reason": "The page presents a project and its outcomes."}
        ]
      }
    ],
    "audiences": [],
    "topics": [],
    "technologies": [
      {
        "id": "python",
        "label": "Python",
        "description": "A general-purpose programming language.",
        "kind": "programming-language",
        "parent": null,
        "aliases": [],
        "evidence": [
          {"file": "docs/example.md", "reason": "The page materially demonstrates Python automation."}
        ]
      }
    ]
  }
}

Every dimension must be present even when empty. `kind` is required for every
technology candidate and must not be used on the other dimensions.
"""

CONSOLIDATION_SYSTEM_PROMPT = r"""
You are the taxonomy architect for a Docusaurus portfolio representing roughly
25 years of technical writing, programming and documentation-engineering
experience. You are given candidates extracted across the repository.

Use British English. Return JSON only.

Produce a high-quality controlled vocabulary for exactly:
content_types, audiences, topics, technologies.

The goal is precision and useful structure, NOT an artificially small
technology list.

Rules:

1. Merge synonyms and near-duplicates.
2. Choose stable reusable concepts.
3. Keep audience, topic, technology and content type semantically distinct.
4. Topics are substantive themes, not every named entity.
5. A technology can remain even if only one document currently evidences it,
   when it materially demonstrates genuine technical experience.
6. Preserve historically meaningful technologies; this is a long-career portfolio.
7. Every technology MUST use one supplied TECHNOLOGY KIND.
8. Companies, employers, clients, customers, manufacturers, consultancies,
   financial institutions and corporate organisations are not technologies.
9. If a company name merely implies a domain, retain the reusable domain as a
   topic when evidence supports it (for example payments), not the company as a
   technology.
10. Products/platforms are technologies only when the evidence concerns the
    technical product/platform itself.
11. IDs must be lower-case kebab-case.
12. Labels must be concise human-readable names.
13. Descriptions define inclusion criteria rather than advertise the concept.
14. Preserve useful aliases only where terminology genuinely varies.
15. Use parent relationships only when they add real hierarchical meaning.
16. Parents must exist in the same dimension.
17. Keep parent hierarchy shallow: no more than two parent levels.
18. Evidence must refer only to files in the supplied candidates.
19. Do not invent evidence.
20. Every final term needs at least one evidence item.
21. Do not invent lifecycle/governance metadata; deterministic tooling adds it.

Return JSON with this exact top-level shape:

{
  "dimensions": {
    "content_types": {"terms": {}},
    "audiences": {"terms": {}},
    "topics": {"terms": {}},
    "technologies": {
      "terms": {
        "python": {
          "label": "Python",
          "description": "A general-purpose programming language.",
          "kind": "programming-language",
          "aliases": []
        }
      }
    }
  },
  "evidence": {
    "content_types": {},
    "audiences": {},
    "topics": {},
    "technologies": {
      "python": [
        {"file": "docs/example.md", "reason": "The page materially demonstrates Python."}
      ]
    }
  }
}

Term objects may contain label, description, parent (optional), aliases
(optional), and for technologies only, kind (required).
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the initial v2 taxonomy with DeepSeek")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch-chars", type=int, default=180_000)
    parser.add_argument("--max-file-chars", type=int, default=120_000)
    parser.add_argument("--max-tokens", type=int, default=24_000)
    parser.add_argument(
        "--introduced-date",
        default=date.today().isoformat(),
        help="Governance introduction date (YYYY-MM-DD); defaults to today",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite an existing taxonomy")
    return parser.parse_args()


def relative_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def markdown_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in MARKDOWN_SUFFIXES:
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        files.append(path)
    return files


def split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    closing = None
    for index in range(1, len(lines)):
        if lines[index].strip() in {"---", "..."}:
            closing = index
            break
    if closing is None:
        return {}, text

    yaml = YAML(typ="safe")
    try:
        parsed = yaml.load("\n".join(lines[1:closing])) or {}
    except Exception:
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    return parsed, "\n".join(lines[closing + 1 :])


def document_for_prompt(path: Path, root: Path, max_file_chars: int) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    front_matter, body = split_front_matter(text)
    title = front_matter.get("title") if isinstance(front_matter.get("title"), str) else ""
    description = (
        front_matter.get("description")
        if isinstance(front_matter.get("description"), str)
        else ""
    )
    if len(body) > max_file_chars:
        body = body[:max_file_chars] + "\n\n[CONTENT TRUNCATED BY TAXONOMY GENERATOR]"
    return {
        "file": relative_path(path, root),
        "title": title.strip(),
        "description": description.strip(),
        "content": body.strip(),
    }


def format_document(document: dict[str, str]) -> str:
    parts = [f"FILE: {document['file']}"]
    if document["title"]:
        parts.append(f"FRONT-MATTER TITLE: {document['title']}")
    if document["description"]:
        parts.append(f"FRONT-MATTER DESCRIPTION: {document['description']}")
    parts.extend(["", "CONTENT:", document["content"], "", f"END FILE: {document['file']}"])
    return "\n".join(parts)


def make_batches(documents: list[dict[str, str]], max_chars: int) -> list[list[dict[str, str]]]:
    batches: list[list[dict[str, str]]] = []
    current: list[dict[str, str]] = []
    size = 0
    for document in documents:
        rendered_size = len(format_document(document))
        if current and size + rendered_size > max_chars:
            batches.append(current)
            current = []
            size = 0
        current.append(document)
        size += rendered_size
    if current:
        batches.append(current)
    return batches


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


def request_deepseek_json(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
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
            {"role": "system", "content": system_prompt},
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
                        "Return the requested result again as one complete, strictly valid JSON "
                        "object. Do not return empty content, Markdown fences or commentary."
                    ),
                }
            )
            time.sleep(2 ** (attempt - 1))
    raise RuntimeError(f"DeepSeek request failed after {attempts} attempts: {last_error}")


def technology_kinds_prompt() -> str:
    return json.dumps(taxonomy_tools.DEFAULT_TECHNOLOGY_KINDS, indent=2, ensure_ascii=False)


def clean_aliases(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(
        {
            item.strip()
            for item in value
            if isinstance(item, str)
            and item.strip()
            and item.strip().casefold() != label.casefold()
        },
        key=str.casefold,
    )


def validate_candidate_response(
    result: dict[str, Any],
    known_files: set[str],
) -> dict[str, list[dict[str, Any]]]:
    candidates = result.get("candidates")
    if not isinstance(candidates, dict):
        raise ValueError("Extraction response is missing candidates")

    allowed_kinds = set(taxonomy_tools.DEFAULT_TECHNOLOGY_KINDS)
    normalised: dict[str, list[dict[str, Any]]] = {}
    for dimension in DISCOVERED_DIMENSIONS:
        raw_terms = candidates.get(dimension, [])
        if not isinstance(raw_terms, list):
            raise ValueError(f"Candidate dimension {dimension!r} must be an array")

        terms: list[dict[str, Any]] = []
        for raw in raw_terms:
            if not isinstance(raw, dict):
                continue
            term_id = raw.get("id")
            label = raw.get("label")
            description = raw.get("description")
            parent = raw.get("parent")
            if not isinstance(term_id, str) or not TERM_ID_RE.fullmatch(term_id):
                continue
            if not isinstance(label, str) or not label.strip():
                continue
            if not isinstance(description, str) or not description.strip():
                continue
            if parent is not None and not isinstance(parent, str):
                parent = None

            term_kind = raw.get("kind")
            if dimension == "technologies":
                if not isinstance(term_kind, str) or term_kind not in allowed_kinds:
                    continue
            elif term_kind is not None:
                # The other dimensions are not typed by technology kind.
                continue

            evidence = []
            raw_evidence = raw.get("evidence", [])
            if isinstance(raw_evidence, list):
                for item in raw_evidence:
                    if not isinstance(item, dict):
                        continue
                    file_path = item.get("file")
                    reason = item.get("reason")
                    if file_path in known_files and isinstance(reason, str) and reason.strip():
                        evidence.append({"file": file_path, "reason": reason.strip()})
            if not evidence:
                continue

            term: dict[str, Any] = {
                "id": term_id,
                "label": label.strip(),
                "description": description.strip(),
                "parent": parent,
                "aliases": clean_aliases(raw.get("aliases"), label.strip()),
                "evidence": evidence,
            }
            if dimension == "technologies":
                term["kind"] = term_kind
            terms.append(term)
        normalised[dimension] = terms
    return normalised


def merge_candidates(
    batches: list[dict[str, list[dict[str, Any]]]],
) -> dict[str, list[dict[str, Any]]]:
    merged: dict[str, dict[str, dict[str, Any]]] = {
        dimension: {} for dimension in DISCOVERED_DIMENSIONS
    }
    for batch in batches:
        for dimension in DISCOVERED_DIMENSIONS:
            for term in batch.get(dimension, []):
                term_id = term["id"]
                existing = merged[dimension].get(term_id)
                if existing is None:
                    merged[dimension][term_id] = json.loads(json.dumps(term))
                    continue

                if dimension == "technologies" and existing.get("kind") != term.get("kind"):
                    # Preserve both signals for consolidation rather than silently choosing.
                    existing.setdefault("alternative_kinds", [])
                    existing["alternative_kinds"] = sorted(
                        set(existing["alternative_kinds"] + [term["kind"]])
                    )

                existing["aliases"] = sorted(
                    set(existing.get("aliases", [])) | set(term.get("aliases", [])),
                    key=str.casefold,
                )
                seen = {(item["file"], item["reason"]) for item in existing["evidence"]}
                for item in term["evidence"]:
                    marker = (item["file"], item["reason"])
                    if marker not in seen:
                        existing["evidence"].append(item)
                        seen.add(marker)
    return {dimension: list(terms.values()) for dimension, terms in merged.items()}


def validate_final_response(
    result: dict[str, Any],
    known_files: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    dimensions = result.get("dimensions")
    evidence = result.get("evidence")
    if not isinstance(dimensions, dict) or not isinstance(evidence, dict):
        raise ValueError("Consolidation response must contain dimensions and evidence objects")

    allowed_kinds = set(taxonomy_tools.DEFAULT_TECHNOLOGY_KINDS)
    final_terms: dict[str, dict[str, Any]] = {}
    final_evidence: dict[str, Any] = {}

    for dimension_id in DISCOVERED_DIMENSIONS:
        raw_dimension = dimensions.get(dimension_id)
        if not isinstance(raw_dimension, dict) or not isinstance(raw_dimension.get("terms"), dict):
            raise ValueError(f"Final dimension {dimension_id!r} is missing terms")
        raw_terms = raw_dimension["terms"]
        clean_terms: dict[str, Any] = {}

        for term_id, raw_term in raw_terms.items():
            if not isinstance(term_id, str) or not TERM_ID_RE.fullmatch(term_id):
                raise ValueError(f"Invalid final term ID {dimension_id}.{term_id}")
            if not isinstance(raw_term, dict):
                raise ValueError(f"Final term {dimension_id}.{term_id} must be an object")
            label = raw_term.get("label")
            description = raw_term.get("description")
            parent = raw_term.get("parent")
            if not isinstance(label, str) or not label.strip():
                raise ValueError(f"Final term {dimension_id}.{term_id} has no label")
            if not isinstance(description, str) or not description.strip():
                raise ValueError(f"Final term {dimension_id}.{term_id} has no description")
            if parent is not None and not isinstance(parent, str):
                raise ValueError(f"Final term {dimension_id}.{term_id} has invalid parent")

            term: dict[str, Any] = {
                "label": label.strip(),
                "description": description.strip(),
            }
            if dimension_id == "technologies":
                kind = raw_term.get("kind")
                if not isinstance(kind, str) or kind not in allowed_kinds:
                    raise ValueError(
                        f"Final technology {term_id!r} must use an allowed technology kind"
                    )
                term["kind"] = kind
            elif raw_term.get("kind") is not None:
                raise ValueError(f"Final non-technology term {dimension_id}.{term_id} may not use kind")

            if parent:
                term["parent"] = parent
            aliases = clean_aliases(raw_term.get("aliases"), label.strip())
            if aliases:
                term["aliases"] = aliases
            clean_terms[term_id] = term

        for term_id, term in clean_terms.items():
            parent = term.get("parent")
            if parent and parent not in clean_terms:
                raise ValueError(
                    f"Final term {dimension_id}.{term_id} refers to missing parent {parent!r}"
                )

        raw_evidence = evidence.get(dimension_id, {})
        if not isinstance(raw_evidence, dict):
            raw_evidence = {}
        clean_evidence: dict[str, list[dict[str, str]]] = {}
        for term_id in clean_terms:
            items = raw_evidence.get(term_id, [])
            valid_items = []
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    file_path = item.get("file")
                    reason = item.get("reason")
                    if file_path in known_files and isinstance(reason, str) and reason.strip():
                        valid_items.append({"file": file_path, "reason": reason.strip()})
            if not valid_items:
                raise ValueError(f"Final term {dimension_id}.{term_id} has no valid evidence")
            clean_evidence[term_id] = valid_items

        final_terms[dimension_id] = clean_terms
        final_evidence[dimension_id] = clean_evidence

    return final_terms, final_evidence


def add_governance(term: dict[str, Any], introduced: str, source: str, review: str) -> dict[str, Any]:
    governed = dict(term)
    governed["governance"] = {
        "status": "active",
        "introduced": introduced,
        "source": source,
        "review": review,
    }
    return governed


def build_taxonomy(final_terms: dict[str, dict[str, Any]], introduced: str) -> dict[str, Any]:
    review = "annual"
    dimensions: dict[str, Any] = {}
    content_type_ids = set(final_terms["content_types"])

    for dimension_id, config in DISCOVERED_DIMENSIONS.items():
        dimension = dict(config)
        if dimension_id == "technologies":
            constraints = {
                type_id: dict(limits)
                for type_id, limits in taxonomy_tools.DEFAULT_TECHNOLOGY_CONSTRAINTS_BY_TYPE.items()
                if type_id in content_type_ids
            }
            if constraints:
                dimension["constraints_by_type"] = constraints
        dimension["terms"] = {
            term_id: add_governance(term, introduced, "initial-taxonomy", review)
            for term_id, term in sorted(final_terms[dimension_id].items())
        }
        dimensions[dimension_id] = dimension

    lifecycle = {key: value for key, value in LIFECYCLE_DIMENSION.items() if key != "terms"}
    lifecycle["terms"] = {
        term_id: add_governance(term, introduced, "policy-seeded", review)
        for term_id, term in LIFECYCLE_DIMENSION["terms"].items()
    }
    dimensions["lifecycle"] = lifecycle

    return {
        "version": taxonomy_tools.TAXONOMY_VERSION,
        "governance": {
            "taxonomy_owner": "repository reviewers",
            "ai_proposals_require_pr_review": True,
            "default_review": review,
        },
        "technology_kinds": json.loads(json.dumps(taxonomy_tools.DEFAULT_TECHNOLOGY_KINDS)),
        "dimensions": dimensions,
    }


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 100
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# Canonical controlled vocabulary for portfolio metadata.\n")
        handle.write("# AI may propose changes, but only reviewed repository changes adopt them.\n\n")
        yaml.dump(data, handle)


def candidate_counts(candidates: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    return {dimension: len(candidates.get(dimension, [])) for dimension in DISCOVERED_DIMENSIONS}


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    output = root / DEFAULT_OUTPUT
    audit_output = root / DEFAULT_AUDIT_OUTPUT

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.introduced_date):
        print("ERROR: --introduced-date must be YYYY-MM-DD", file=sys.stderr)
        return 2
    for path in (output, audit_output):
        if path.exists() and not args.force:
            print(f"ERROR: {path} exists; use --force to overwrite", file=sys.stderr)
            return 2

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("ERROR: DEEPSEEK_API_KEY is not set", file=sys.stderr)
        return 2

    paths = markdown_files(root)
    if not paths:
        print("ERROR: no Markdown/MDX files found", file=sys.stderr)
        return 2

    documents = [document_for_prompt(path, root, args.max_file_chars) for path in paths]
    known_files = {document["file"] for document in documents}
    batches = make_batches(documents, args.batch_chars)
    print(f"found {len(documents)} Markdown/MDX files in {len(batches)} extraction batch(es)")

    kinds_json = technology_kinds_prompt()
    extracted: list[dict[str, list[dict[str, Any]]]] = []
    for index, batch in enumerate(batches, start=1):
        batch_files = {document["file"] for document in batch}
        print(f"extracting candidates from batch {index}/{len(batches)} ({len(batch)} files)")
        result = request_deepseek_json(
            api_key=api_key,
            model=args.model,
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            user_prompt=(
                "ALLOWED TECHNOLOGY KINDS:\n"
                + kinds_json
                + "\n\nAnalyse these repository documents and return candidate taxonomy terms as JSON.\n\n"
                + "\n\n".join(format_document(document) for document in batch)
            ),
            max_tokens=args.max_tokens,
        )
        validated = validate_candidate_response(result, batch_files)
        extracted.append(validated)
        print("  " + ", ".join(f"{key}={value}" for key, value in candidate_counts(validated).items()))

    merged = merge_candidates(extracted)
    print(
        "merged candidates: "
        + ", ".join(f"{key}={value}" for key, value in candidate_counts(merged).items())
    )
    print("consolidating repository-wide taxonomy")

    final_result = request_deepseek_json(
        api_key=api_key,
        model=args.model,
        system_prompt=CONSOLIDATION_SYSTEM_PROMPT,
        user_prompt=(
            "ALLOWED TECHNOLOGY KINDS:\n"
            + kinds_json
            + "\n\nConsolidate these repository-wide candidates into the initial controlled taxonomy. "
            "Return JSON only.\n\n"
            + json.dumps({"candidate_taxonomy_terms": merged}, indent=2, ensure_ascii=False)
        ),
        max_tokens=args.max_tokens,
    )
    final_terms, final_evidence = validate_final_response(final_result, known_files)
    taxonomy = build_taxonomy(final_terms, args.introduced_date)

    taxonomy_tools.validate_taxonomy_schema(taxonomy, root / taxonomy_tools.SCHEMA_PATH)
    taxonomy_tools.validate_taxonomy_semantics(taxonomy)
    write_yaml(output, taxonomy)
    taxonomy_tools.generate_derived_files(root, taxonomy)

    audit = {
        "generator": {
            "taxonomy_version": taxonomy_tools.TAXONOMY_VERSION,
            "model": args.model,
            "introduced_date": args.introduced_date,
            "source_file_count": len(documents),
            "extraction_batch_count": len(batches),
        },
        "technology_kinds": taxonomy_tools.DEFAULT_TECHNOLOGY_KINDS,
        "source_files": sorted(known_files),
        "candidate_counts": candidate_counts(merged),
        "final_counts": {dimension: len(final_terms[dimension]) for dimension in DISCOVERED_DIMENSIONS},
        "candidates": merged,
        "evidence": final_evidence,
    }
    audit_output.parent.mkdir(parents=True, exist_ok=True)
    audit_output.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"wrote {output.relative_to(root).as_posix()}")
    print(f"wrote {audit_output.relative_to(root).as_posix()}")
    print("review the taxonomy before running taxonomy_ai.py --all --apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
