#!/usr/bin/env python3
"""DeepSeek-assisted metadata classification and taxonomy-gap suggestions.

AI output is advisory by default. Deterministic repository state remains the
source of truth and the only basis for blocking CI.

This version is deliberately tolerant at the AI boundary:

- Existing terms are resolved by ID, label or alias rather than requiring the
  model to reproduce repository IDs perfectly.
- A proposal that resolves to an existing term is folded into normal metadata
  instead of failing the document.
- Proposal evidence is verified/recovered from the actual document text.
- One invalid proposal is dropped with a warning; it does not invalidate the
  rest of the document classification.
- Over-cardinality AI selections are trimmed deterministically with a warning.
  Under-cardinality required metadata still fails the document classification.
- All governed taxonomy metadata is normalised to arrays, including dimensions
  such as content type and lifecycle whose maximum cardinality is one.

Examples:

  python scripts/taxonomy_ai.py docs/skills/APIDocumentation.md
  python scripts/taxonomy_ai.py --changed-base origin/main
  python scripts/taxonomy_ai.py --all
  python scripts/taxonomy_ai.py --apply-from taxonomy/taxonomy-ai-suggestions.json

Normal classification runs are review-only: they write Markdown and JSON review
artifacts without modifying repository state. `--apply-from` applies the exact
saved JSON artifact without calling the model again. The legacy `--all --apply`
workflow is deprecated and rejected because it combines a fresh corpus-wide AI
run with immediate mutation. Targeted `--apply` remains available for backwards
compatibility. Nothing is committed or pushed; `git diff` remains the final
human approval surface.
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
from typing import Any, Iterable

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

- Every value inside the top-level `metadata` object MUST be a JSON array of
  taxonomy IDs, including single-selection dimensions such as `type` and
  `lifecycle`. Never return a scalar taxonomy value.
- A dimension with `multiple=false` still uses an array; its cardinality rules
  determine how many values may appear in that array.
- Existing taxonomy values are preferred whenever they adequately represent the
  document.
- Select only values materially supported by the supplied document.
- Prefer precise metadata over indiscriminate tagging.
- Respect global and content-type-specific cardinality constraints.
- Prefer exact existing IDs, but deterministic tooling will also resolve labels
  and aliases if necessary.
- Never silently invent an ID and use it as though it already exists.
- Lifecycle is policy-controlled: choose an existing lifecycle value and never
  propose a lifecycle term.
- A new term may be proposed only in a dimension marked ai_managed=true.

PAGE FIELD POLICY:

- `title` and `description` are ordinary top-level Docusaurus front-matter
  fields, not taxonomy dimensions.
- Suggest `title` only when the current top-level `title` field is absent, null,
  empty, or whitespace-only. If a usable title already exists, return null for
  `page_fields.title` and do not rewrite it.
- Suggest `description` only when the current top-level `description` field is
  absent, null, empty, or whitespace-only. If a usable description already
  exists, return null for `page_fields.description` and do not rewrite it.
- A suggested title must be concise, specific to the document, plain text, and
  suitable as the page title.
- A suggested description must be concise plain text suitable for Docusaurus
  metadata and the portfolio Browse card. Prefer one informative sentence and
  do not use Markdown.
- Existing nested card text such as
  `sidebar_custom_props.sampleCard.description` may be used as evidence/context,
  but it does not count as the top-level `description` field.
- Never invent claims that are not supported by the document.

TECHNOLOGY POLICY:

- The technology vocabulary is intentionally broad because the portfolio spans
  a long career. Historical technologies are valid professional evidence.
- A technology must be materially used, documented, implemented, tested,
  explained or demonstrated by the page.
- Foundational and specialised technologies are distinct capabilities. For
  example Python + Flask, JavaScript + React, OpenAPI + Postman, Git + GitHub
  Actions may all be selected together when supported.
- Every technology term has a controlled `kind`. New technology proposals MUST
  use one of the supplied technology kind IDs.
- Companies, employers, clients, customers, consultancies, manufacturers,
  banks/financial institutions and other corporate organisations are NOT
  technologies.
- Do not classify a company name as a technology simply because technical work
  was performed for that company.
- A software product/platform sharing a company/brand name can be a technology
  only when the document is materially about using that product/platform.
- Reusable technical methods are allowed when a supplied kind such as
  modelling-methodology, architecture-style or technical-technique applies.

TAXONOMY EXPANSION HAS A HIGH BAR. Propose a new term only when:

1. The concept is substantively present in this document.
2. No existing term accurately represents it.
3. The concept is reusable and reasonably likely to classify other content, OR
   it is significant evidence of genuine professional technology experience.
4. It is meaningfully distinct from existing terms and aliases.
5. It is not merely a project/client/employer/company name or passing mention.

For each proposed term provide a concise rationale plus `evidence_hints`:
short phrases identifying where the evidence appears. They do not need to be
perfect quotations; deterministic tooling will locate and preserve the exact
source text. Do not invent evidence that is absent from the document.

Return exactly this top-level JSON shape:

{
  "page_fields": {
    "title": "Suggested title when the current top-level title is missing, otherwise null",
    "description": "Suggested description when the current top-level description is missing, otherwise null"
  },
  "metadata": {
    "type": ["case-study"],
    "audiences": ["developers"],
    "topics": ["api-documentation"],
    "technologies": ["openapi"],
    "lifecycle": ["current"]
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
      "reason": "Why the existing vocabulary is insufficient.",
      "evidence_hints": ["phrase identifying the relevant source evidence"]
    }
  ]
}

For proposals outside technologies, omit `kind`. Use an empty proposal array
when the existing taxonomy is sufficient. Do not include Markdown fences or
commentary.
"""

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in",
    "is", "it", "of", "on", "or", "that", "the", "this", "to", "used", "using",
    "with", "was", "were", "into", "through", "tool", "technology", "platform",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Suggest page fields and taxonomy metadata with DeepSeek")
    parser.add_argument("paths", nargs="*", help="docs Markdown/MDX files or directories")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    parser.add_argument("--all", action="store_true", help="Review every docs/**/*.md[x] file")
    parser.add_argument("--changed-base", help="Review docs changed since this git SHA")
    parser.add_argument(
        "--apply-from",
        type=Path,
        help=(
            "Apply one previously reviewed taxonomy-ai JSON artifact without calling the model. "
            "Cannot be combined with document selection or --model."
        ),
    )
    parser.add_argument(
        "--model",
        default=None,
        help=f"DeepSeek model for classification runs (default: {DEFAULT_MODEL})",
    )
    parser.add_argument("--max-file-chars", type=int, default=120_000)
    parser.add_argument("--max-tokens", type=int, default=8_000)
    parser.add_argument("--output", type=Path, default=DEFAULT_MARKDOWN_REPORT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument(
        "--introduced-date",
        default=date.today().isoformat(),
        help="Introduction date recorded in generated review artifacts and for targeted --apply",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Apply a targeted classification run immediately. Deprecated with --all; "
            "prefer review followed by --apply-from."
        ),
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
            if response.status_code == 429 or response.status_code >= 500:
                raise requests.HTTPError(
                    f"DeepSeek returned HTTP {response.status_code}: {response.text[:500]}",
                    response=response,
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

    # Include page-level fields needed for conditional title/description
    # suggestions. Keep selected supporting Docusaurus front matter as context,
    # including existing nested sample-card copy when present.
    for field in (
        "title",
        "description",
        "sidebar_custom_props",
        "slug",
        "id",
        "sidebar_label",
    ):
        if field in front_matter:
            current[field] = plain_value(front_matter[field])

    for dimension in dimensions.values():
        field = dimension["metadata_field"]
        if field in front_matter:
            current[field] = plain_value(front_matter[field])
    if "tags" in front_matter:
        current["tags"] = plain_value(front_matter["tags"])
    if len(body) > max_chars:
        body = body[:max_chars] + "\n\n[CONTENT TRUNCATED FOR AI CLASSIFICATION]"
    return current, body


def has_usable_front_matter_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def normalise_page_field_suggestion(value: Any) -> str | None:
    """Return one clean plain-text suggestion, or None for an unusable value."""
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def missing_page_field_suggestions(
    result: dict[str, Any],
    current: dict[str, Any],
) -> list[str]:
    """Return missing top-level page fields that still lack usable AI suggestions."""
    raw_page_fields = result.get("page_fields")
    if not isinstance(raw_page_fields, dict):
        raw_page_fields = {}

    missing: list[str] = []
    for field in ("title", "description"):
        if has_usable_front_matter_string(current.get(field)):
            continue
        if normalise_page_field_suggestion(raw_page_fields.get(field)) is None:
            missing.append(field)
    return missing


def validate_page_field_suggestions(
    result: dict[str, Any],
    current: dict[str, Any],
    warnings: list[dict[str, Any]],
) -> dict[str, str]:
    """Validate conditional AI suggestions for top-level title/description.

    Existing usable values are immutable at the AI layer: even if the model
    returns replacement copy, it is ignored. Only genuinely missing/blank
    top-level fields are eligible for suggestions.
    """
    raw_page_fields = result.get("page_fields")
    if raw_page_fields is None:
        raw_page_fields = {}
    if not isinstance(raw_page_fields, dict):
        warnings.append(
            {
                "code": "invalid-page-fields",
                "message": "Ignored malformed page_fields; expected an object.",
            }
        )
        raw_page_fields = {}

    suggestions: dict[str, str] = {}
    for field in ("title", "description"):
        current_value = current.get(field)
        missing = not has_usable_front_matter_string(current_value)
        raw_value = raw_page_fields.get(field)

        if not missing:
            if normalise_page_field_suggestion(raw_value):
                warnings.append(
                    {
                        "code": "ignored-existing-page-field",
                        "message": (
                            f"Ignored AI page_fields.{field} because the document "
                            f"already has a usable top-level {field!r} field."
                        ),
                    }
                )
            continue

        suggestion = normalise_page_field_suggestion(raw_value)
        if suggestion is None:
            warnings.append(
                {
                    "code": "missing-page-field-suggestion",
                    "message": (
                        f"Top-level {field!r} is missing, but DeepSeek did not "
                        f"return a usable page_fields.{field} suggestion."
                    ),
                }
            )
            continue

        suggestions[field] = suggestion

    return suggestions


def clean_string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return list(value)


def normalise_ai_metadata_values(
    value: Any,
    *,
    field: str,
    required: bool,
    warnings: list[dict[str, Any]],
) -> list[str]:
    """Normalise AI metadata to the repository's array storage contract.

    The prompt requires arrays for every taxonomy dimension. A scalar string is
    still tolerated at the AI boundary for backwards compatibility and is
    wrapped in a one-item list with an advisory warning. Other malformed values
    fail required fields and are ignored for optional fields.
    """

    values = clean_string_list(value)
    if values is not None:
        return values

    if isinstance(value, str):
        warnings.append(
            {
                "code": "normalised-scalar-metadata",
                "message": (
                    f"Normalised scalar metadata.{field} {value!r} to a one-item array."
                ),
            }
        )
        return [value]

    if required:
        raise ValueError(f"metadata.{field} must be an array of IDs/labels")

    if value is not None:
        warnings.append(
            {
                "code": "invalid-optional-metadata",
                "message": f"Ignored malformed optional metadata.{field}; expected an array.",
            }
        )
    return []


def active_term_ids(dimension: dict[str, Any]) -> set[str]:
    return set(taxonomy_tools.active_terms(dimension))


def normalise_lookup(value: str) -> str:
    text = value.casefold().strip()
    text = text.replace("++", " plus plus ").replace("#", " sharp ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def build_term_index(dimension: dict[str, Any]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for term_id, term in taxonomy_tools.active_terms(dimension).items():
        names = [term_id, term["label"], *term.get("aliases", [])]
        for name in names:
            key = normalise_lookup(name)
            if key:
                index.setdefault(key, set()).add(term_id)
    return index


def resolve_existing_term(value: str, dimension: dict[str, Any]) -> tuple[str | None, str | None]:
    active = taxonomy_tools.active_terms(dimension)
    if value in active:
        return value, "exact-id"

    key = normalise_lookup(value)
    matches = build_term_index(dimension).get(key, set())
    if len(matches) == 1:
        return next(iter(matches)), "label-or-alias"
    if len(matches) > 1:
        return None, "ambiguous"
    return None, None


def resolve_proposal_term(value: str, proposals: Iterable[dict[str, Any]]) -> str | None:
    key = normalise_lookup(value)
    matches: set[str] = set()
    for proposal in proposals:
        names = [proposal["id"], proposal["label"], *proposal.get("aliases", [])]
        if any(normalise_lookup(name) == key for name in names):
            matches.add(proposal["id"])
    if len(matches) == 1:
        return next(iter(matches))
    return None


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


def organisation_like_signals(description: str) -> list[str]:
    return [
        name
        for name, pattern in taxonomy_tools.ORGANISATION_LIKE_DESCRIPTION_PATTERNS
        if pattern.search(description)
    ]


def sentence_or_line_chunks(text: str) -> list[str]:
    chunks: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", stripped):
            sentence = sentence.strip()
            if sentence:
                chunks.append(sentence)
    return chunks


def tokenise(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[A-Za-z0-9+#.]+", value.casefold())
        if len(token) >= 2 and token not in STOPWORDS
    }


def exact_case_insensitive_excerpt(document_text: str, needle: str) -> str | None:
    if not needle.strip():
        return None
    match = re.search(re.escape(needle.strip()), document_text, re.IGNORECASE)
    if not match:
        return None
    start = max(
        document_text.rfind("\n", 0, match.start()) + 1,
        document_text.rfind(". ", 0, match.start()) + 2,
    )
    line_end = document_text.find("\n", match.end())
    sentence_end = document_text.find(". ", match.end())
    ends = [end for end in (line_end, sentence_end + 1 if sentence_end >= 0 else -1) if end >= 0]
    end = min(ends) if ends else min(len(document_text), match.end() + 220)
    excerpt = document_text[start:end].strip()
    return excerpt[:400] if excerpt else document_text[match.start():match.end()]


def recover_evidence(
    document_text: str,
    *,
    label: str,
    aliases: list[str],
    term_id: str,
    hints: list[str],
    max_items: int = 3,
) -> list[str]:
    evidence: list[str] = []

    # 1. Preserve model evidence when it is already exact.
    for hint in hints:
        if hint and hint in document_text:
            evidence.append(hint.strip())
        elif hint:
            excerpt = exact_case_insensitive_excerpt(document_text, hint)
            if excerpt:
                evidence.append(excerpt)
        if len(evidence) >= max_items:
            return list(dict.fromkeys(evidence))[:max_items]

    # 2. Search canonical names/aliases and preserve actual source context.
    name_needles = [label, *aliases, term_id.replace("-", " ")]
    for needle in name_needles:
        excerpt = exact_case_insensitive_excerpt(document_text, needle)
        if excerpt:
            evidence.append(excerpt)
        if len(evidence) >= max_items:
            return list(dict.fromkeys(evidence))[:max_items]

    # 3. Deterministic token-overlap recovery for paraphrased evidence hints.
    chunks = sentence_or_line_chunks(document_text)
    best: list[tuple[float, str]] = []
    for hint in hints:
        hint_tokens = tokenise(hint)
        if not hint_tokens:
            continue
        for chunk in chunks:
            chunk_tokens = tokenise(chunk)
            if not chunk_tokens:
                continue
            overlap = len(hint_tokens & chunk_tokens)
            if not overlap:
                continue
            score = overlap / len(hint_tokens)
            # Require two shared meaningful tokens where possible, or a very
            # strong match for a one-token hint.
            if overlap >= 2 or score >= 0.8:
                best.append((score, chunk[:400]))
    for _score, chunk in sorted(best, key=lambda item: (-item[0], len(item[1]))):
        evidence.append(chunk)
        if len(list(dict.fromkeys(evidence))) >= max_items:
            break

    return list(dict.fromkeys(evidence))[:max_items]


def proposal_existing_match(
    raw: dict[str, Any],
    dimension: dict[str, Any],
) -> tuple[str | None, str | None]:
    probes = []
    for key in ("id", "label"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            probes.append(value.strip())
    aliases = raw.get("aliases", [])
    if isinstance(aliases, list):
        probes.extend(item.strip() for item in aliases if isinstance(item, str) and item.strip())

    for probe in probes:
        resolved, method = resolve_existing_term(probe, dimension)
        if resolved:
            return resolved, method
    return None, None


def validate_one_proposal(
    raw: Any,
    *,
    taxonomy: dict[str, Any],
    document_text: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
    """Return (accepted proposal, warning, folded_existing_id)."""

    if not isinstance(raw, dict):
        return None, {"code": "invalid-proposal", "message": "Proposal is not an object."}, None

    dimensions = taxonomy["dimensions"]
    kind_ids = set(taxonomy["technology_kinds"])
    dimension_id = raw.get("dimension")
    term_id = raw.get("id")
    label = raw.get("label")
    description = raw.get("description")
    kind = raw.get("kind")
    parent = raw.get("parent")
    aliases = raw.get("aliases", [])
    reason = raw.get("reason")

    if dimension_id not in dimensions:
        return None, {
            "code": "invalid-proposal",
            "message": f"Proposal uses unknown dimension {dimension_id!r}.",
        }, None
    dimension = dimensions[dimension_id]
    if not dimension["ai_managed"]:
        return None, {
            "code": "invalid-proposal",
            "message": f"AI may not propose terms in {dimension_id!r}.",
        }, None

    existing_id, match_method = proposal_existing_match(raw, dimension)
    if existing_id:
        return None, {
            "code": "folded-existing-proposal",
            "message": (
                f"Proposal {dimension_id}.{term_id or label!s} resolves to existing term "
                f"{existing_id!r}; reused the existing term instead of proposing a duplicate."
            ),
            "dimension": dimension_id,
            "existing_id": existing_id,
            "match_method": match_method,
        }, existing_id

    if not isinstance(term_id, str) or not TERM_ID_RE.fullmatch(term_id):
        return None, {
            "code": "invalid-proposal",
            "message": f"Invalid proposed term ID {term_id!r}.",
        }, None
    if not isinstance(label, str) or not label.strip():
        return None, {
            "code": "invalid-proposal",
            "message": f"Proposal {dimension_id}.{term_id} has no label.",
        }, None
    if not isinstance(description, str) or not description.strip():
        return None, {
            "code": "invalid-proposal",
            "message": f"Proposal {dimension_id}.{term_id} has no description.",
        }, None

    if dimension_id == "technologies":
        if not isinstance(kind, str) or kind not in kind_ids:
            return None, {
                "code": "invalid-technology-kind",
                "message": (
                    f"Technology proposal {term_id!r} does not use an approved technology kind."
                ),
            }, None
        signals = organisation_like_signals(description)
        if signals:
            return None, {
                "code": "organisation-like-technology",
                "message": (
                    f"Dropped technology proposal {term_id!r}: description looks organisation-like "
                    f"({', '.join(signals)})."
                ),
            }, None
    elif kind is not None:
        return None, {
            "code": "invalid-proposal",
            "message": f"Proposal {dimension_id}.{term_id} must not contain kind.",
        }, None

    if parent is not None and not isinstance(parent, str):
        return None, {
            "code": "invalid-proposal",
            "message": f"Proposal {dimension_id}.{term_id} has invalid parent.",
        }, None
    if not isinstance(aliases, list) or not all(isinstance(item, str) for item in aliases):
        return None, {
            "code": "invalid-proposal",
            "message": f"Proposal {dimension_id}.{term_id} aliases must be strings.",
        }, None
    if not isinstance(reason, str) or not reason.strip():
        return None, {
            "code": "invalid-proposal",
            "message": f"Proposal {dimension_id}.{term_id} has no rationale.",
        }, None

    clean_alias_list = clean_aliases(aliases, label.strip())
    raw_hints = raw.get("evidence_hints", raw.get("evidence", []))
    hints = (
        [item.strip() for item in raw_hints if isinstance(item, str) and item.strip()]
        if isinstance(raw_hints, list)
        else []
    )
    evidence = recover_evidence(
        document_text,
        label=label.strip(),
        aliases=clean_alias_list,
        term_id=term_id,
        hints=hints,
    )
    if not evidence:
        return None, {
            "code": "unverified-evidence",
            "message": (
                f"Dropped proposal {dimension_id}.{term_id}: no exact source evidence could be "
                "recovered from the document."
            ),
        }, None

    proposal: dict[str, Any] = {
        "dimension": dimension_id,
        "id": term_id,
        "label": label.strip(),
        "description": description.strip(),
        "parent": parent,
        "aliases": clean_alias_list,
        "reason": reason.strip(),
        "evidence": evidence,
        "evidence_hints": hints,
    }
    if dimension_id == "technologies":
        proposal["kind"] = kind
    return proposal, None, None


def dedupe_preserve_order(values: list[str]) -> tuple[list[str], bool]:
    seen: set[str] = set()
    result: list[str] = []
    had_duplicates = False
    for value in values:
        if value in seen:
            had_duplicates = True
            continue
        seen.add(value)
        result.append(value)
    return result, had_duplicates


def validate_ai_result(
    result: dict[str, Any],
    taxonomy: dict[str, Any],
    document_text: str,
    current: dict[str, Any],
) -> dict[str, Any]:
    metadata = result.get("metadata")
    reasons = result.get("selection_reasons")
    raw_proposals = result.get("proposed_taxonomy_terms")
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")
    if not isinstance(reasons, dict):
        reasons = {}
    if not isinstance(raw_proposals, list):
        raise ValueError("proposed_taxonomy_terms must be an array")

    dimensions = taxonomy["dimensions"]
    warnings: list[dict[str, Any]] = []
    page_field_suggestions = validate_page_field_suggestions(result, current, warnings)
    proposals: list[dict[str, Any]] = []
    folded_existing: dict[str, set[str]] = {dimension_id: set() for dimension_id in dimensions}

    # Validate proposals individually. A bad proposal is advisory noise, not a
    # reason to discard otherwise valid document metadata.
    for raw in raw_proposals:
        proposal, warning, folded_id = validate_one_proposal(
            raw, taxonomy=taxonomy, document_text=document_text
        )
        if warning:
            warnings.append(warning)
        if proposal:
            proposals.append(proposal)
        if folded_id and isinstance(raw, dict) and raw.get("dimension") in dimensions:
            folded_existing[raw["dimension"]].add(folded_id)

    proposed_by_dimension: dict[str, list[dict[str, Any]]] = {
        dimension_id: [] for dimension_id in dimensions
    }
    for proposal in proposals:
        proposed_by_dimension[proposal["dimension"]].append(proposal)

    # Parent validation is per proposal and non-fatal. Drop only proposals with
    # unresolved parents.
    accepted_proposals: list[dict[str, Any]] = []
    proposed_ids_all = {
        dimension_id: {proposal["id"] for proposal in items}
        for dimension_id, items in proposed_by_dimension.items()
    }
    for proposal in proposals:
        parent = proposal.get("parent")
        if parent:
            dimension_id = proposal["dimension"]
            resolved_parent, _ = resolve_existing_term(parent, dimensions[dimension_id])
            if resolved_parent:
                proposal["parent"] = resolved_parent
            elif parent not in proposed_ids_all[dimension_id]:
                warnings.append(
                    {
                        "code": "unknown-proposal-parent",
                        "message": (
                            f"Dropped proposal {dimension_id}.{proposal['id']}: parent {parent!r} "
                            "does not resolve to an existing or simultaneously proposed term."
                        ),
                    }
                )
                continue
        accepted_proposals.append(proposal)
    proposals = accepted_proposals
    proposed_by_dimension = {dimension_id: [] for dimension_id in dimensions}
    for proposal in proposals:
        proposed_by_dimension[proposal["dimension"]].append(proposal)

    # Content type first because it determines per-type cardinality limits.
    # The repository stores every taxonomy dimension as an array, even when its
    # maximum cardinality is one. Scalar model output is tolerated and
    # normalised only at this AI boundary.
    type_dimension = dimensions["content_types"]
    type_field = type_dimension["metadata_field"]
    raw_type_values = normalise_ai_metadata_values(
        metadata.get(type_field),
        field=type_field,
        required=True,
        warnings=warnings,
    )
    if not raw_type_values:
        raise ValueError(f"metadata.{type_field} must contain one content type")
    if len(raw_type_values) > 1:
        warnings.append(
            {
                "code": "trimmed-cardinality",
                "message": (
                    f"Trimmed metadata.{type_field} from {len(raw_type_values)} to 1 value "
                    "before applying content-type-specific cardinality rules."
                ),
            }
        )
        raw_type_values = raw_type_values[:1]

    raw_type = raw_type_values[0]
    type_value, method = resolve_existing_term(raw_type, type_dimension)
    if not type_value:
        type_value = resolve_proposal_term(raw_type, proposed_by_dimension["content_types"])
        method = "proposed-term" if type_value else method
    if not type_value:
        raise ValueError(
            f"metadata.{type_field} does not resolve to a declared/proposed content type: {raw_type!r}"
        )
    if method != "exact-id":
        warnings.append(
            {
                "code": "canonicalised-metadata",
                "message": f"Resolved metadata.{type_field} {raw_type!r} to canonical ID {type_value!r}.",
            }
        )

    clean_metadata: dict[str, Any] = {}
    for dimension_id, dimension in dimensions.items():
        field = dimension["metadata_field"]
        raw_value = metadata.get(field)

        if dimension_id == "content_types":
            raw_values = [type_value]
        else:
            raw_values = normalise_ai_metadata_values(
                raw_value,
                field=field,
                required=dimension["required"],
                warnings=warnings,
            )

        resolved_values: list[str] = []
        if dimension_id == "content_types":
            resolved_values = [type_value]
        else:
            for raw_item in raw_values:
                resolved, resolve_method = resolve_existing_term(raw_item, dimension)
                if not resolved:
                    resolved = resolve_proposal_term(raw_item, proposed_by_dimension[dimension_id])
                    if resolved:
                        resolve_method = "proposed-term"
                if not resolved:
                    # If a proposal was folded into an existing term, the raw
                    # metadata may still contain the proposed ID/label. Attempt
                    # to map it through the folded existing set by normalised
                    # comparison against the original raw proposals.
                    folded_match = None
                    for raw_proposal in raw_proposals:
                        if not isinstance(raw_proposal, dict) or raw_proposal.get("dimension") != dimension_id:
                            continue
                        probes = [raw_proposal.get("id"), raw_proposal.get("label")]
                        if any(
                            isinstance(probe, str)
                            and normalise_lookup(probe) == normalise_lookup(raw_item)
                            for probe in probes
                        ):
                            folded_match, _ = proposal_existing_match(raw_proposal, dimension)
                            if folded_match:
                                break
                    resolved = folded_match
                    if resolved:
                        resolve_method = "folded-existing-proposal"

                if not resolved:
                    warnings.append(
                        {
                            "code": "unknown-metadata-term",
                            "message": f"Dropped unresolved metadata.{field} value {raw_item!r}.",
                        }
                    )
                    continue
                resolved_values.append(resolved)
                if resolve_method != "exact-id":
                    warnings.append(
                        {
                            "code": "canonicalised-metadata",
                            "message": f"Resolved metadata.{field} {raw_item!r} to canonical ID {resolved!r}.",
                        }
                    )

            # Folded duplicate proposals are genuine existing selections. Add
            # them if the model proposed them but omitted them from metadata.
            for folded_id in sorted(folded_existing[dimension_id]):
                if folded_id not in resolved_values:
                    resolved_values.append(folded_id)
                    warnings.append(
                        {
                            "code": "folded-existing-proposal",
                            "message": f"Added existing term {folded_id!r} to metadata.{field} from a redundant AI proposal.",
                        }
                    )

            # An accepted new proposal is, by definition, materially evidenced
            # by this document. For multi-valued dimensions, include it in the
            # document metadata even if the model forgot to repeat its new ID
            # in the metadata array. Single-cardinality dimensions remain
            # selection-policy controlled and are not auto-expanded here.
            if dimension["multiple"]:
                for proposal in proposed_by_dimension[dimension_id]:
                    proposal_id = proposal["id"]
                    if proposal_id not in resolved_values:
                        resolved_values.append(proposal_id)
                        warnings.append(
                            {
                                "code": "added-proposed-term-to-metadata",
                                "message": f"Added proposed term {proposal_id!r} to metadata.{field} because the proposal has verified document evidence.",
                            }
                        )

        resolved_values, had_duplicates = dedupe_preserve_order(resolved_values)
        if had_duplicates:
            warnings.append(
                {
                    "code": "duplicate-metadata",
                    "message": f"Removed duplicate IDs from metadata.{field}.",
                }
            )

        minimum, maximum = taxonomy_tools.effective_limits(dimension, type_value)
        if len(resolved_values) > maximum:
            original_count = len(resolved_values)
            resolved_values = resolved_values[:maximum]
            warnings.append(
                {
                    "code": "trimmed-cardinality",
                    "message": (
                        f"Trimmed metadata.{field} from {original_count} to {maximum} values to satisfy "
                        f"cardinality for content type {type_value!r}."
                    ),
                }
            )
        if len(resolved_values) < minimum:
            raise ValueError(
                f"metadata.{field} has {len(resolved_values)} valid value(s) after canonicalisation; "
                f"minimum is {minimum} for content type {type_value!r}"
            )

        # Repository storage contract: every governed taxonomy field is a YAML
        # list, even when cardinality permits exactly one value.
        clean_metadata[field] = resolved_values

    clean_reasons: dict[str, str] = {}
    for dimension in dimensions.values():
        field = dimension["metadata_field"]
        reason = reasons.get(field)
        if isinstance(reason, str) and reason.strip():
            clean_reasons[field] = reason.strip()
        else:
            clean_reasons[field] = "AI classification; no rationale supplied."
            warnings.append(
                {
                    "code": "missing-rationale",
                    "message": f"selection_reasons.{field} was missing; retained the classification without a rationale.",
                }
            )

    return {
        "page_field_suggestions": page_field_suggestions,
        "metadata": clean_metadata,
        "selection_reasons": clean_reasons,
        "proposed_taxonomy_terms": proposals,
        "warnings": warnings,
    }


def make_user_prompt(
    path: Path,
    root: Path,
    taxonomy: dict[str, Any],
    current: dict[str, Any],
    body: str,
) -> str:
    missing_page_fields = [
        field
        for field in ("title", "description")
        if not has_usable_front_matter_string(current.get(field))
    ]
    existing_page_fields = [
        field
        for field in ("title", "description")
        if has_usable_front_matter_string(current.get(field))
    ]

    page_field_requirements = [
        "PAGE FIELD REQUIREMENTS FOR THIS DOCUMENT:",
    ]
    if missing_page_fields:
        page_field_requirements.append(
            "- REQUIRED: return a non-empty plain-text suggestion in `page_fields` "
            "for each of these missing top-level fields: "
            + ", ".join(missing_page_fields)
            + "."
        )
    else:
        page_field_requirements.append(
            "- No top-level title/description fields are missing."
        )

    if existing_page_fields:
        page_field_requirements.append(
            "- These top-level fields already have usable values and MUST be returned "
            "as null in `page_fields`: "
            + ", ".join(existing_page_fields)
            + "."
        )

    page_field_requirements.append(
        "- Do not omit the `page_fields` object from the JSON response."
    )

    return (
        "Classify this document using the controlled taxonomy below. Return JSON only.\n\n"
        + "\n".join(page_field_requirements)
        + "\n\nCONTROLLED TAXONOMY:\n"
        + json.dumps(taxonomy_for_prompt(taxonomy), indent=2, ensure_ascii=False)
        + "\n\nFILE: "
        + path.relative_to(root).as_posix()
        + "\nCURRENT FRONT MATTER (relevant fields):\n"
        + json.dumps(current, indent=2, ensure_ascii=False)
        + "\n\nDOCUMENT CONTENT:\n"
        + body
    )


def merge_global_proposals(results: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    warnings: list[str] = []
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
                warnings.append(
                    f"Conflicting proposals for {key[0]}.{key[1]} across documents; kept the first definition for human review."
                )
            existing["proposed_by_files"].append(file_path)
            existing["evidence"] = list(dict.fromkeys(existing["evidence"] + proposal["evidence"]))
            if proposal["reason"] not in existing["reason"]:
                existing["reason"] += " " + proposal["reason"]
    return [merged[key] for key in sorted(merged)], warnings


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
    document_errors: list[dict[str, str]],
    global_warnings: list[str],
) -> str:
    """Render an action-oriented human review report.

    The report puts the two review decisions first:

    1. Accept/reject the suggested metadata.
    2. Accept/reject any proposed additions to the controlled vocabulary.

    Rationale and validation notes follow afterwards as supporting evidence.
    """

    lines = [
        "# Taxonomy AI review",
        "",
        f"Model: `{model}`",
        "",
        "> Advisory only. Repository taxonomy and deterministic validation remain authoritative.",
        "",
    ]

    if document_errors:
        lines.extend(["## Classification errors", ""])
        for error in document_errors:
            lines.append(f"- `{error['file']}`: {error['error']}")
        lines.append("")

    if global_warnings:
        lines.extend(["## Cross-document proposal warnings", ""])
        lines.extend(f"- {warning}" for warning in global_warnings)
        lines.append("")

    if not results:
        lines.extend(["No documentation files produced a usable AI classification.", ""])
        return "\n".join(lines)

    yaml = YAML()
    yaml.default_flow_style = False

    for result_index, result in enumerate(results):
        lines.extend(
            [
                f"**Document:** `{result['file']}`",
                "",
                "## Suggested page fields",
                "",
            ]
        )

        page_field_suggestions = result.get("page_field_suggestions", {})
        if page_field_suggestions:
            lines.extend(
                [
                    "Only missing top-level fields are shown; existing title/description values are retained.",
                    "",
                    "```yaml",
                ]
            )
            page_stream = io.StringIO()
            yaml.dump(page_field_suggestions, page_stream)
            lines.extend([page_stream.getvalue().rstrip(), "```", ""])
        else:
            lines.extend(
                [
                    "None. The document already has usable top-level title and description fields, "
                    "or DeepSeek did not return a usable suggestion.",
                    "",
                ]
            )

        lines.extend(
            [
                "## Suggested taxonomy metadata",
                "",
                "Review these values before applying them.",
                "",
                "```yaml",
            ]
        )

        stream = io.StringIO()
        yaml.dump(result["metadata"], stream)
        lines.extend([stream.getvalue().rstrip(), "```", ""])

        lines.extend(["## Proposed new taxonomy terms", ""])
        file_proposals = result["proposed_taxonomy_terms"]

        if not file_proposals:
            lines.extend(
                [
                    "None. The existing controlled vocabulary is sufficient for this document.",
                    "",
                ]
            )
        else:
            for proposal in file_proposals:
                kind_suffix = (
                    f" — kind `{proposal['kind']}`"
                    if proposal.get("kind")
                    else ""
                )
                lines.extend(
                    [
                        f"### `{proposal['dimension']}.{proposal['id']}` — "
                        f"{proposal['label']}{kind_suffix}",
                        "",
                        f"**Why propose it:** {proposal['reason']}",
                        "",
                        "**Suggested definition**",
                        "",
                        "```yaml",
                        yaml_snippet_for_proposal(proposal),
                        "```",
                        "",
                        "**Verified source evidence**",
                        "",
                    ]
                )
                for excerpt in proposal["evidence"]:
                    lines.append(f"- `{excerpt}`")
                lines.append("")

        lines.extend(["## Why these metadata values", ""])
        for field, reason in result["selection_reasons"].items():
            lines.append(f"- **{field}**: {reason}")
        lines.append("")

        if result.get("warnings"):
            lines.extend(["## Normalisation / validation notes", ""])
            for warning in result["warnings"]:
                lines.append(f"- {warning['message']}")
            lines.append("")

        if result_index < len(results) - 1:
            lines.extend(["---", ""])

    # Keep consolidated proposals for batch CLI runs only. In the normal
    # single-document Front Matter workflow this would just duplicate the
    # proposal section above.
    if proposals and len(results) > 1:
        lines.extend(["# Consolidated taxonomy proposals", ""])
        for proposal in proposals:
            files = ", ".join(
                f"`{item}`" for item in proposal["proposed_by_files"]
            )
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


def load_review_artifact(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"review artifact does not exist: {path}")
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"review artifact is not valid JSON: {error}") from error
    if not isinstance(artifact, dict):
        raise ValueError("review artifact root must be a JSON object")
    return artifact


def validate_review_artifact(
    root: Path,
    taxonomy: dict[str, Any],
    artifact: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    """Validate a saved review artifact before applying it.

    This validates the saved, already-canonicalised result against the current
    taxonomy without calling an LLM. Content/taxonomy fingerprints are a later
    hardening step; this function deliberately implements only the reviewed
    artifact CLI contract.
    """
    version = artifact.get("taxonomy_version")
    if version != taxonomy_tools.TAXONOMY_VERSION or version != taxonomy.get("version"):
        raise ValueError(
            f"review artifact taxonomy version {version!r} does not match current "
            f"taxonomy version {taxonomy.get('version')!r}"
        )

    introduced = artifact.get("introduced_date")
    if not isinstance(introduced, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", introduced):
        raise ValueError(
            "review artifact has no valid introduced_date; regenerate it with the updated taxonomy_ai.py"
        )

    errors = artifact.get("errors", [])
    if not isinstance(errors, list):
        raise ValueError("review artifact errors must be an array")
    if errors:
        raise ValueError(
            "refusing to apply a review artifact containing document-level classification errors"
        )

    results = artifact.get("results")
    proposals = artifact.get("consolidated_proposals")
    if not isinstance(results, list) or not all(isinstance(item, dict) for item in results):
        raise ValueError("review artifact results must be an array of objects")
    if not isinstance(proposals, list) or not all(isinstance(item, dict) for item in proposals):
        raise ValueError("review artifact consolidated_proposals must be an array of objects")
    if not results:
        raise ValueError("review artifact contains no document classifications to apply")

    # A proposal in a generated artifact was new at review time. If its ID now
    # exists, canonical taxonomy state changed after review; do not silently skip it.
    for proposal in proposals:
        dimension_id = proposal.get("dimension")
        term_id = proposal.get("id")
        if dimension_id not in taxonomy["dimensions"] or not isinstance(term_id, str):
            raise ValueError("review artifact contains an invalid consolidated proposal")
        if term_id in taxonomy["dimensions"][dimension_id]["terms"]:
            raise ValueError(
                f"review artifact is stale: {dimension_id}.{term_id} now exists in the canonical taxonomy"
            )

    proposal_ids: dict[str, set[str]] = {dimension_id: set() for dimension_id in taxonomy["dimensions"]}
    for proposal in proposals:
        proposal_ids[proposal["dimension"]].add(proposal["id"])

    for result in results:
        relative = result.get("file")
        metadata = result.get("metadata")
        if not isinstance(relative, str) or not relative:
            raise ValueError("review artifact result is missing file")
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError as error:
            raise ValueError(f"review artifact file is outside repository root: {relative}") from error
        if not path.is_file():
            raise ValueError(f"review artifact file no longer exists: {relative}")
        if not isinstance(metadata, dict):
            raise ValueError(f"{relative}: review artifact metadata must be an object")

        type_dimension = taxonomy["dimensions"]["content_types"]
        type_field = type_dimension["metadata_field"]
        type_values = metadata.get(type_field)
        if not isinstance(type_values, list) or len(type_values) != 1 or not isinstance(type_values[0], str):
            raise ValueError(f"{relative}: saved metadata.{type_field} must contain exactly one taxonomy ID")
        content_type = type_values[0]

        for dimension_id, dimension in taxonomy["dimensions"].items():
            field = dimension["metadata_field"]
            values = metadata.get(field)
            if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
                raise ValueError(f"{relative}: saved metadata.{field} must be an array of taxonomy IDs")
            minimum, maximum = taxonomy_tools.effective_limits(dimension, content_type)
            if len(values) < minimum or len(values) > maximum:
                raise ValueError(
                    f"{relative}: saved metadata.{field} violates current cardinality {minimum}..{maximum}"
                )
            active_ids = set(taxonomy_tools.active_terms(dimension))
            allowed_ids = active_ids | proposal_ids[dimension_id]
            unknown = [value for value in values if value not in allowed_ids]
            if unknown:
                raise ValueError(
                    f"{relative}: saved metadata.{field} contains unknown/non-active IDs: "
                    + ", ".join(sorted(unknown))
                )

        page_fields = result.get("page_field_suggestions", {})
        if not isinstance(page_fields, dict):
            raise ValueError(f"{relative}: page_field_suggestions must be an object")
        for field, value in page_fields.items():
            if field not in {"title", "description"} or not isinstance(value, str) or not value.strip():
                raise ValueError(f"{relative}: invalid saved page field suggestion {field!r}")

    return results, proposals, introduced


def apply_review_artifact(root: Path, artifact_path: Path) -> None:
    artifact = load_review_artifact(artifact_path)
    taxonomy = taxonomy_tools.load_and_validate_taxonomy(root)
    results, proposals, introduced = validate_review_artifact(root, taxonomy, artifact)
    apply_results(root, taxonomy, results, proposals, introduced)


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

        # Page-field suggestions are intentionally conservative: --apply fills
        # only missing/blank top-level title/description fields and never
        # overwrites an existing usable value.
        for field, value in result.get("page_field_suggestions", {}).items():
            if field not in {"title", "description"}:
                continue
            if not has_usable_front_matter_string(front_matter.get(field)):
                front_matter[field] = value

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

    # Phase 2: apply an already reviewed JSON artifact. This path is deliberately
    # deterministic: it performs no model calls and therefore needs no API key.
    if args.apply_from is not None:
        conflicts = []
        if args.paths:
            conflicts.append("paths")
        if args.all:
            conflicts.append("--all")
        if args.changed_base:
            conflicts.append("--changed-base")
        if args.model is not None:
            conflicts.append("--model")
        if args.apply:
            conflicts.append("--apply")
        if conflicts:
            print(
                "ERROR: --apply-from cannot be combined with " + ", ".join(conflicts),
                file=sys.stderr,
            )
            return 2

        artifact_path = args.apply_from if args.apply_from.is_absolute() else root / args.apply_from
        try:
            apply_review_artifact(root, artifact_path)
        except Exception as error:
            print(f"ERROR: failed to apply reviewed artifact: {error}", file=sys.stderr)
            return 1
        try:
            artifact_display = artifact_path.relative_to(root).as_posix()
        except ValueError:
            artifact_display = str(artifact_path)
        print(
            f"Applied reviewed AI artifact {artifact_display}. "
            "No model call was made. Review `git diff` before committing."
        )
        return 0

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.introduced_date):
        print("ERROR: --introduced-date must be YYYY-MM-DD", file=sys.stderr)
        return 2

    modes = int(bool(args.paths)) + int(bool(args.all)) + int(bool(args.changed_base))
    if modes != 1:
        print(
            "ERROR: choose exactly one of explicit paths, --all, --changed-base, or --apply-from",
            file=sys.stderr,
        )
        return 2

    if args.all and args.apply:
        print(
            "ERROR: --all --apply is deprecated and no longer supported. "
            "Run `python scripts/taxonomy_ai.py --all`, review the Markdown/JSON report, "
            "then run `python scripts/taxonomy_ai.py --apply-from "
            "taxonomy/taxonomy-ai-suggestions.json`.",
            file=sys.stderr,
        )
        return 2

    model = args.model or DEFAULT_MODEL
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
            user_prompt = make_user_prompt(path, root, taxonomy, current, body)
            raw = request_json(
                api_key,
                model,
                user_prompt,
                args.max_tokens,
            )

            missing_page_fields = missing_page_field_suggestions(raw, current)
            if missing_page_fields:
                print(
                    f"NOTE: {relative}: DeepSeek omitted required page field suggestion(s): "
                    + ", ".join(missing_page_fields)
                    + "; retrying page-field generation.",
                    file=sys.stderr,
                )
                repair_prompt = (
                    user_prompt
                    + "\n\nCORRECTION REQUIRED:\n"
                    + "Your previous response omitted one or more REQUIRED page-field suggestions. "
                    + "Return the complete JSON object again. In `page_fields`, provide non-empty "
                    + "plain-text suggestions for exactly these missing top-level fields: "
                    + ", ".join(missing_page_fields)
                    + ". Existing usable title/description fields must remain null. "
                    + "Do not omit `page_fields`."
                )
                repaired = request_json(
                    api_key,
                    model,
                    repair_prompt,
                    args.max_tokens,
                )
                repaired_page_fields = repaired.get("page_fields")
                if isinstance(repaired_page_fields, dict):
                    raw["page_fields"] = repaired_page_fields

            validated = validate_ai_result(raw, taxonomy, body, current)
            validated["file"] = relative
            validated["current_metadata"] = current
            results.append(validated)
            for warning in validated.get("warnings", []):
                print(f"NOTE: {relative}: {warning['message']}", file=sys.stderr)
        except Exception as error:
            errors.append({"file": relative, "error": str(error)})
            print(f"WARNING: {relative}: {error}", file=sys.stderr)

    proposals, global_warnings = merge_global_proposals(results)
    for warning in global_warnings:
        print(f"NOTE: {warning}", file=sys.stderr)

    markdown_report = render_markdown_report(
        results, proposals, model, errors, global_warnings
    )
    output = args.output if args.output.is_absolute() else root / args.output
    json_output = args.json_output if args.json_output.is_absolute() else root / args.json_output
    output.parent.mkdir(parents=True, exist_ok=True)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown_report, encoding="utf-8")
    json_output.write_text(
        json.dumps(
            {
                "taxonomy_version": taxonomy_tools.TAXONOMY_VERSION,
                "model": model,
                "introduced_date": args.introduced_date,
                "results": results,
                "consolidated_proposals": proposals,
                "global_warnings": global_warnings,
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
    if not args.apply:
        print(
            "review the report, then apply this exact artifact with: "
            f"python scripts/taxonomy_ai.py --apply-from {json_output.relative_to(root).as_posix()}"
        )

    if args.apply:
        print(
            "WARNING: direct --apply is retained only for targeted compatibility. "
            "For audited changes, review the generated report and use --apply-from instead.",
            file=sys.stderr,
        )
        if errors:
            print(
                "ERROR: refusing --apply because one or more documents had no usable AI classification. "
                "Proposal-level warnings do not block apply, but document-level failures do.",
                file=sys.stderr,
            )
            return 1
        try:
            apply_results(root, taxonomy, results, proposals, args.introduced_date)
        except Exception as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print("AI suggestions applied to the working tree. Review `git diff` before committing.")

    # Proposal-level warnings are advisory. Only document-level classification
    # failures produce a non-zero status.
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
