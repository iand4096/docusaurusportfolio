#!/usr/bin/env python3
"""Create the initial v2 controlled taxonomy from repository Markdown/MDX.

The generator deliberately separates *discovery* from *consolidation*:

1. Batch extraction for content types, audiences and topics.
2. High-recall technology extraction for every individual document.
3. A repository coverage-audit pass that looks specifically for technologies
   missed by the per-document extractor.
4. Cached, chunked consolidation per dimension so large candidate sets do not
   produce one oversized request. Chunk results are reconciled using compact
   provenance IDs.
5. A generation checkpoint and content-addressed response cache make reruns
   resumable after interruption or API timeouts.
6. Deterministic restoration of validated foundational technology candidates
   if consolidation accidentally drops them.
7. Schema/semantic validation and generation of Docusaurus/Front Matter files.

The technology inventory is intentionally broad: this portfolio represents a
long technical-writing/programming career. Companies, employers, clients and
other corporate entities are explicitly excluded from the technology
dimension, while real products/platforms may be retained when the document is
about using the technical product itself.

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
import hashlib
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
DEFAULT_EXTRACTION_MODEL = "deepseek-v4-flash"
DEFAULT_CONSOLIDATION_MODEL = "deepseek-v4-pro"
DEFAULT_OUTPUT = Path("taxonomy/taxonomy.yml")
DEFAULT_AUDIT_OUTPUT = Path("taxonomy/taxonomy-generation.json")
DEFAULT_CHECKPOINT_OUTPUT = Path("taxonomy/taxonomy-generation-checkpoint.json")
DEFAULT_CACHE_DIR = Path("taxonomy/.generation-cache")
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
        # This is a per-document ceiling, not a limit on the size of the taxonomy.
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

# These kinds should not be silently removed during consolidation when the
# high-recall extraction phase found genuine evidence for them. They represent
# foundational capabilities that remain useful portfolio/search facets even
# when more specialised tools are also present.
FOUNDATIONAL_PRESERVE_KINDS = {
    "programming-language",
    "shell-scripting",
    "markup-content-language",
    "data-format",
    "runtime",
    "standard-specification",
    "protocol",
    "version-control",
    "architecture-style",
}

# Deterministic coverage warnings. These do NOT automatically create taxonomy
# terms; they flag suspicious omissions for human review and the audit file.
FOUNDATIONAL_COVERAGE_PATTERNS: dict[str, dict[str, Any]] = {
    "python": {
        "label": "Python",
        "kind": "programming-language",
        "patterns": [r"\bPython\b"],
    },
    "java": {
        "label": "Java",
        "kind": "programming-language",
        "patterns": [r"\bJava\b"],
    },
    "javascript": {
        "label": "JavaScript",
        "kind": "programming-language",
        "patterns": [r"\bJavaScript\b"],
    },
    "typescript": {
        "label": "TypeScript",
        "kind": "programming-language",
        "patterns": [r"\bTypeScript\b"],
    },
    "scala": {
        "label": "Scala",
        "kind": "programming-language",
        "patterns": [r"\bScala\b"],
    },
    "c-plus-plus": {
        "label": "C++",
        "kind": "programming-language",
        "patterns": [r"(?<!\w)C\+\+(?!\w)"],
    },
    "c-sharp": {
        "label": "C#",
        "kind": "programming-language",
        "patterns": [r"(?<!\w)C#(?!\w)"],
    },
    "node-js": {
        "label": "Node.js",
        "kind": "runtime",
        "patterns": [r"\bNode\.js\b", r"\bNodeJS\b"],
    },
    "openapi": {
        "label": "OpenAPI",
        "kind": "standard-specification",
        "patterns": [r"\bOpenAPI\b"],
    },
    "markdown": {
        "label": "Markdown",
        "kind": "markup-content-language",
        "patterns": [r"\bMarkdown\b"],
    },
    "mdx": {
        "label": "MDX",
        "kind": "markup-content-language",
        "patterns": [r"\bMDX\b"],
    },
    "json": {
        "label": "JSON",
        "kind": "data-format",
        "patterns": [r"\bJSON\b"],
    },
    "yaml": {
        "label": "YAML",
        "kind": "data-format",
        "patterns": [r"\bYAML\b"],
    },
    "git": {
        "label": "Git",
        "kind": "version-control",
        "patterns": [r"\bGit\b"],
    },
    "docker": {
        "label": "Docker",
        "kind": "container-platform",
        "patterns": [r"\bDocker\b"],
    },
    "kubernetes": {
        "label": "Kubernetes",
        "kind": "container-platform",
        "patterns": [r"\bKubernetes\b"],
    },
}

NONTECH_EXTRACTION_SYSTEM_PROMPT = r"""
You are performing controlled-vocabulary discovery for a Docusaurus portfolio
representing roughly 25 years of technical writing, programming,
documentation engineering, API work and systems experience.

Use British English. Return JSON only.

Discover candidates for exactly three dimensions:

- content_types: structural/editorial page types represented by the corpus.
- audiences: groups for whom the content is materially relevant.
- topics: reusable subject areas substantially discussed by the content.

Do NOT extract technologies in this pass; technologies are handled separately
with a high-recall per-document process.

Rules:

- Base every candidate on supplied repository content.
- Prefer reusable concepts, not every noun or heading.
- Do not create near-duplicate synonyms.
- Do not use navigation boilerplate as evidence.
- Do not infer unsupported audiences.
- Do not use the portfolio author's name as taxonomy metadata.
- Do not use employer/client/project/company names as topics unless they truly
  represent a reusable subject domain (for example `payments`).
- IDs must be stable lower-case kebab-case.
- Evidence FILE values must exactly match supplied FILE values.
- Keep evidence reasons concise.

Return exactly:

{
  "candidates": {
    "content_types": [],
    "audiences": [],
    "topics": []
  }
}

A candidate has: id, label, description, optional parent, optional aliases,
and evidence [{"file": "...", "reason": "..."}].
"""

TECHNOLOGY_EXTRACTION_SYSTEM_PROMPT = r"""
You are performing HIGH-RECALL technology extraction from ONE portfolio
document. This is candidate discovery, not taxonomy pruning.

Use British English. Return JSON only.

Identify ALL genuine technologies that the author materially used, implemented,
configured, programmed with, integrated, tested, documented, explained or
demonstrated in this document.

The portfolio represents roughly 25 years of technical writing, programming,
documentation engineering, API work and systems experience. Historical
technologies are valid professional evidence.

CRITICAL RECALL RULES:

- Do not summarise a stack by keeping only its specialised components.
- Foundational and specialised technologies must BOTH be returned when the
  document materially supports both.
- Python + Flask -> return BOTH Python and Flask.
- Python + Requests -> return BOTH Python and Requests.
- JavaScript + React -> return BOTH JavaScript and React.
- Java + Jetty -> return BOTH Java and Jetty.
- OpenAPI + Postman -> return BOTH OpenAPI and Postman.
- C++ + CATIA integration -> return BOTH C++ and CATIA when both are materially
  demonstrated.
- Git + GitHub Actions -> return BOTH when both are materially used.
- Docker + Kubernetes -> return BOTH when both are materially used.
- Do not omit a programming language because frameworks/libraries for that
  language are present.
- Do not omit a standard/specification because tools implementing it are
  present.
- Do not omit a runtime because applications running on it are present.
- False negatives are more harmful in this pass than reasonable redundancy;
  later consolidation removes duplicates and weak candidates.

ENTITY-TYPE RULES:

- Every technology MUST use one supplied TECHNOLOGY KIND.
- Companies, employers, clients, customers, consultancies, manufacturers,
  banks/financial institutions and other corporate organisations are NEVER
  technologies merely because they appear in technical project content.
- A product/platform sharing a company/brand name may be a technology only when
  the document is materially about using that technical product/platform.
- Example: Docusaurus -> technology; Mastercard -> organisation, not technology.
- Example: AMX Composer -> technology; AMX as the company -> not technology.
- Example: Paysafe.js -> technology; Paysafe as the corporate entity -> not technology.
- Reusable technical methods are allowed when a supplied kind such as
  modelling-methodology, architecture-style or technical-technique applies.

OTHER RULES:

- Do not classify a passing mention as substantive technical experience.
- IDs must be stable lower-case kebab-case identifiers.
- Evidence FILE must exactly match the supplied FILE value.
- Keep descriptions and evidence reasons concise.

Return exactly:

{
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
"""

COVERAGE_AUDIT_SYSTEM_PROMPT = r"""
You are performing a SECOND-PASS technology coverage audit for a long-career
technical portfolio.

Use British English. Return JSON only.

You are given:
1. one or more source documents; and
2. the technology candidates already extracted from the repository.

Find only MATERIAL technologies present in the supplied documents that are
missing from the existing candidate inventory.

Pay particular attention to omissions of:
- programming languages;
- shell/scripting environments;
- markup/content languages and data formats;
- runtimes;
- API specifications and standards;
- protocols;
- frameworks and libraries;
- documentation platforms/tools;
- CI/CD and version-control technologies;
- containers/infrastructure;
- security/cryptography technologies;
- developer tools.

Foundational and specialised technologies are distinct capabilities. For
example, Python must not disappear merely because Flask or Requests is present;
JavaScript must not disappear because React is present; OpenAPI must not
disappear because Postman is present.

Do not repeat a candidate already represented by ID, label or alias. Do not add
companies, employers, clients or other organisations. Every returned technology
must use one supplied TECHNOLOGY KIND and have source evidence.

Return exactly:

{
  "technologies": []
}
"""

CHUNK_CONSOLIDATION_SYSTEM_PROMPT = r"""
You are consolidating ONE dimension of a controlled taxonomy for a Docusaurus
portfolio representing roughly 25 years of technical writing, programming and
documentation-engineering experience.

Use British English. Return JSON only.

This is an intermediate reduction pass. Merge only true synonyms, spelling
variants and near-duplicates. Preserve distinct professional capabilities.
Do not optimise for the smallest possible taxonomy.

For technologies:
- every term MUST use one supplied technology kind;
- companies, employers, clients and corporate organisations are not technologies;
- products/platforms are valid only when the evidence concerns using the
  technical product itself;
- foundational and specialised technologies are distinct capabilities, e.g.
  Python + Flask, JavaScript + React, OpenAPI + Postman, Git + GitHub Actions;
- preserve historically meaningful technologies.

IMPORTANT PROVENANCE RULE:
Do NOT reproduce source evidence. Instead, every returned term MUST contain a
non-empty `source_ids` array listing the input candidate IDs represented by the
consolidated term. Use only source IDs supplied in the input.

Do not create parent relationships in this intermediate pass.

Return exactly:
{
  "terms": {
    "canonical-id": {
      "label": "Canonical label",
      "description": "Concise definition",
      "kind": "technology-kind-only-for-technologies",
      "aliases": [],
      "source_ids": ["input-id"]
    }
  }
}

For non-technology dimensions omit `kind`.
"""

FINAL_RECONCILIATION_SYSTEM_PROMPT = r"""
You are performing the final reconciliation of ONE controlled-taxonomy
dimension for a Docusaurus portfolio representing roughly 25 years of technical
writing, programming and documentation-engineering experience.

Use British English. Return JSON only.

The input has already been reduced in smaller chunks. Reconcile duplicates that
may have fallen into different chunks, normalise IDs/labels/descriptions, and
produce the final terms for this dimension.

Do NOT aggressively prune legitimate portfolio experience. In particular, do
not remove foundational technologies merely because specialised technologies
also exist: Python + Flask, JavaScript + React, Java + Jetty, OpenAPI + Postman,
Git + GitHub Actions, Docker + Kubernetes may all coexist.

For technologies:
- every term MUST use one supplied technology kind;
- organisations/companies/employers/clients are not technologies;
- historically meaningful technologies may remain even if used by one page.

PROVENANCE:
Every returned term MUST contain a non-empty `source_ids` array. These IDs refer
to ORIGINAL extraction candidate IDs and must be selected only from the
`source_ids` arrays present in the input. Do not invent evidence or source IDs.

You may add a `parent` only when the parent is another returned term in this
same dimension and it adds real value. Keep hierarchy shallow.

Return exactly:
{
  "terms": {
    "canonical-id": {
      "label": "Canonical label",
      "description": "Concise definition",
      "kind": "technology-kind-only-for-technologies",
      "aliases": [],
      "source_ids": ["original-candidate-id"],
      "parent": "optional-parent-id"
    }
  }
}

For non-technology dimensions omit `kind`.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the initial v2 taxonomy with DeepSeek")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    parser.add_argument(
        "--model",
        help="Backward-compatible override: use this model for extraction, coverage and consolidation",
    )
    parser.add_argument("--extraction-model", default=DEFAULT_EXTRACTION_MODEL)
    parser.add_argument("--coverage-model", default=DEFAULT_EXTRACTION_MODEL)
    parser.add_argument("--chunk-consolidation-model", default=DEFAULT_EXTRACTION_MODEL)
    parser.add_argument("--consolidation-model", default=DEFAULT_CONSOLIDATION_MODEL)
    parser.add_argument("--batch-chars", type=int, default=180_000)
    parser.add_argument(
        "--consolidation-chunk-size",
        type=int,
        default=60,
        help="Maximum candidate terms in each intermediate consolidation call",
    )
    parser.add_argument(
        "--request-timeout",
        type=int,
        default=180,
        help="HTTP timeout in seconds for each DeepSeek attempt",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
        help="Cache directory for resumable DeepSeek calls",
    )
    parser.add_argument("--no-cache", action="store_true", help="Disable DeepSeek response cache")
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Ignore cached responses and replace them with fresh responses",
    )
    parser.add_argument("--max-file-chars", type=int, default=120_000)
    parser.add_argument("--max-tokens", type=int, default=24_000)
    parser.add_argument(
        "--introduced-date",
        default=date.today().isoformat(),
        help="Governance introduction date (YYYY-MM-DD); defaults to today",
    )
    parser.add_argument("--skip-coverage-audit", action="store_true")
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
    timeout_seconds: int = 180,
    label: str = "DeepSeek request",
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
        started = time.monotonic()
        print(
            f"  -> {label}: attempt {attempt}/{attempts} with {model} ",
            f"(timeout {timeout_seconds}s)",
            flush=True,
        )
        try:
            response = requests.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=timeout_seconds,
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
            parsed = parse_model_json(content)
            elapsed = time.monotonic() - started
            print(f"  <- {label}: completed in {elapsed:.1f}s", flush=True)
            return parsed
        except (requests.RequestException, json.JSONDecodeError, KeyError, IndexError, ValueError) as error:
            last_error = error
            elapsed = time.monotonic() - started
            print(f"  !! {label}: attempt {attempt} failed after {elapsed:.1f}s: {error}", file=sys.stderr, flush=True)
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


def _safe_cache_label(label: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip("-")
    return safe[:80] or "request"


def cached_deepseek_json(
    *,
    root: Path,
    cache_dir: Path,
    use_cache: bool,
    refresh_cache: bool,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    timeout_seconds: int,
    label: str,
) -> dict[str, Any]:
    fingerprint_payload = json.dumps(
        {
            "model": model,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "max_tokens": max_tokens,
        },
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    fingerprint = hashlib.sha256(fingerprint_payload).hexdigest()
    absolute_cache_dir = cache_dir if cache_dir.is_absolute() else root / cache_dir
    cache_path = absolute_cache_dir / f"{_safe_cache_label(label)}-{fingerprint[:16]}.json"

    if use_cache and not refresh_cache and cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if cached.get("fingerprint") == fingerprint and isinstance(cached.get("result"), dict):
                print(f"  == {label}: using cached response {cache_path.relative_to(root) if cache_path.is_relative_to(root) else cache_path}", flush=True)
                return cached["result"]
        except (OSError, json.JSONDecodeError):
            pass

    result = request_deepseek_json(
        api_key=api_key,
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=max_tokens,
        timeout_seconds=timeout_seconds,
        label=label,
    )

    if use_cache:
        absolute_cache_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "fingerprint": fingerprint,
            "label": label,
            "model": model,
            "result": result,
        }
        cache_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result

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


def organisation_like_signals(description: str) -> list[str]:
    return [
        name
        for name, pattern in taxonomy_tools.ORGANISATION_LIKE_DESCRIPTION_PATTERNS
        if pattern.search(description)
    ]


def validate_candidate_terms(
    raw_terms: Any,
    *,
    dimension: str,
    known_files: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if not isinstance(raw_terms, list):
        raise ValueError(f"Candidate dimension {dimension!r} must be an array")

    allowed_kinds = set(taxonomy_tools.DEFAULT_TECHNOLOGY_KINDS)
    terms: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []

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
                rejected.append({"id": term_id, "reason": "invalid or missing technology kind"})
                continue
            signals = organisation_like_signals(description)
            if signals:
                rejected.append(
                    {
                        "id": term_id,
                        "reason": (
                            "organisation-like technology description: " + ", ".join(signals)
                        ),
                    }
                )
                continue
        elif term_kind is not None:
            continue

        evidence: list[dict[str, str]] = []
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

    return terms, rejected


def validate_nontech_response(
    result: dict[str, Any],
    known_files: set[str],
) -> dict[str, list[dict[str, Any]]]:
    candidates = result.get("candidates")
    if not isinstance(candidates, dict):
        raise ValueError("Non-technology extraction response is missing candidates")
    output: dict[str, list[dict[str, Any]]] = {"technologies": []}
    for dimension in ("content_types", "audiences", "topics"):
        terms, _ = validate_candidate_terms(
            candidates.get(dimension, []), dimension=dimension, known_files=known_files
        )
        output[dimension] = terms
    return output


def validate_technology_response(
    result: dict[str, Any],
    known_files: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    return validate_candidate_terms(
        result.get("technologies", []), dimension="technologies", known_files=known_files
    )


def merge_candidates(
    candidate_sets: list[dict[str, list[dict[str, Any]]]],
) -> dict[str, list[dict[str, Any]]]:
    merged: dict[str, dict[str, dict[str, Any]]] = {
        dimension: {} for dimension in DISCOVERED_DIMENSIONS
    }
    for candidate_set in candidate_sets:
        for dimension in DISCOVERED_DIMENSIONS:
            for term in candidate_set.get(dimension, []):
                term_id = term["id"]
                existing = merged[dimension].get(term_id)
                if existing is None:
                    merged[dimension][term_id] = json.loads(json.dumps(term))
                    continue

                if dimension == "technologies" and existing.get("kind") != term.get("kind"):
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


def normalise_lookup(value: str) -> str:
    text = value.casefold().strip()
    text = text.replace("++", " plus plus ").replace("#", " sharp ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def represented_by_terms(term: dict[str, Any], terms: dict[str, dict[str, Any]]) -> bool:
    needles = {
        normalise_lookup(term["id"]),
        normalise_lookup(term["label"]),
        *(normalise_lookup(alias) for alias in term.get("aliases", [])),
    }
    for term_id, existing in terms.items():
        haystack = {
            normalise_lookup(term_id),
            normalise_lookup(existing["label"]),
            *(normalise_lookup(alias) for alias in existing.get("aliases", [])),
        }
        if needles & haystack:
            return True
    return False



def _candidate_for_consolidation(term: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {
        "id": term["id"],
        "label": term["label"],
        "description": term["description"],
        "aliases": term.get("aliases", []),
        "source_ids": term.get("source_ids", [term["id"]]),
    }
    if term.get("kind"):
        compact["kind"] = term["kind"]
    if term.get("alternative_kinds"):
        compact["alternative_kinds"] = term["alternative_kinds"]
    return compact


def _chunk_terms(terms: list[dict[str, Any]], chunk_size: int) -> list[list[dict[str, Any]]]:
    if chunk_size < 1:
        raise ValueError("--consolidation-chunk-size must be at least 1")
    ordered = sorted(
        terms,
        key=lambda item: (
            str(item.get("kind", "")),
            normalise_lookup(str(item.get("label", item.get("id", "")))),
            item.get("id", ""),
        ),
    )
    return [ordered[index : index + chunk_size] for index in range(0, len(ordered), chunk_size)]


def validate_consolidated_dimension_response(
    result: dict[str, Any],
    *,
    dimension: str,
    allowed_source_ids: set[str],
    allow_parent: bool,
) -> dict[str, dict[str, Any]]:
    raw_terms = result.get("terms")
    if not isinstance(raw_terms, dict):
        raise ValueError(f"Consolidation response for {dimension} must contain a terms object")

    allowed_kinds = set(taxonomy_tools.DEFAULT_TECHNOLOGY_KINDS)
    clean: dict[str, dict[str, Any]] = {}
    for term_id, raw in raw_terms.items():
        if not isinstance(term_id, str) or not TERM_ID_RE.fullmatch(term_id):
            raise ValueError(f"Invalid consolidated term ID {dimension}.{term_id}")
        if not isinstance(raw, dict):
            raise ValueError(f"Consolidated term {dimension}.{term_id} must be an object")
        label = raw.get("label")
        description = raw.get("description")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"Consolidated term {dimension}.{term_id} has no label")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"Consolidated term {dimension}.{term_id} has no description")

        raw_source_ids = raw.get("source_ids")
        if not isinstance(raw_source_ids, list):
            raise ValueError(f"Consolidated term {dimension}.{term_id} has no source_ids array")
        source_ids = sorted(
            {
                source_id
                for source_id in raw_source_ids
                if isinstance(source_id, str) and source_id in allowed_source_ids
            }
        )
        if not source_ids:
            raise ValueError(
                f"Consolidated term {dimension}.{term_id} has no valid original source_ids"
            )

        term: dict[str, Any] = {
            "id": term_id,
            "label": label.strip(),
            "description": description.strip(),
            "aliases": clean_aliases(raw.get("aliases"), label.strip()),
            "source_ids": source_ids,
        }
        if dimension == "technologies":
            kind = raw.get("kind")
            if not isinstance(kind, str) or kind not in allowed_kinds:
                raise ValueError(f"Consolidated technology {term_id!r} has invalid kind")
            signals = organisation_like_signals(description)
            if signals:
                raise ValueError(
                    f"Consolidated technology {term_id!r} looks organisation-like "
                    f"({', '.join(signals)})"
                )
            term["kind"] = kind
        elif raw.get("kind") is not None:
            raise ValueError(f"Non-technology term {dimension}.{term_id} may not use kind")

        parent = raw.get("parent")
        if allow_parent and isinstance(parent, str) and parent:
            term["parent"] = parent
        clean[term_id] = term

    if allow_parent:
        for term_id, term in clean.items():
            parent = term.get("parent")
            if parent and parent not in clean:
                raise ValueError(
                    f"Consolidated term {dimension}.{term_id} refers to missing parent {parent!r}"
                )
    return clean


def _deterministic_merge_consolidated_terms(
    terms: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge exact/normalised duplicates before the final reconciliation call."""
    merged: dict[str, dict[str, Any]] = {}
    lookup_to_id: dict[str, str] = {}
    for term in terms:
        keys = [
            normalise_lookup(term["id"]),
            normalise_lookup(term["label"]),
            *(normalise_lookup(alias) for alias in term.get("aliases", [])),
        ]
        existing_id = next((lookup_to_id[key] for key in keys if key in lookup_to_id), None)
        if existing_id is None:
            item = json.loads(json.dumps(term))
            merged[item["id"]] = item
            for key in keys:
                lookup_to_id[key] = item["id"]
            continue

        existing = merged[existing_id]
        existing["source_ids"] = sorted(set(existing["source_ids"]) | set(term["source_ids"]))
        existing["aliases"] = sorted(
            set(existing.get("aliases", [])) | set(term.get("aliases", [])), key=str.casefold
        )
    return list(merged.values())


def consolidate_dimension(
    *,
    root: Path,
    dimension: str,
    candidates: list[dict[str, Any]],
    api_key: str,
    kinds_json: str,
    chunk_model: str,
    final_model: str,
    chunk_size: int,
    max_tokens: int,
    timeout_seconds: int,
    cache_dir: Path,
    use_cache: bool,
    refresh_cache: bool,
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, str]]]]:
    if not candidates:
        return {}, {}

    original_by_id = {term["id"]: term for term in candidates}
    original_ids = set(original_by_id)
    chunks = _chunk_terms(candidates, chunk_size)
    intermediate: list[dict[str, Any]] = []

    print(
        f"consolidating {dimension}: {len(candidates)} candidates in {len(chunks)} chunk(s)",
        flush=True,
    )
    for index, chunk in enumerate(chunks, start=1):
        compact = [_candidate_for_consolidation(term) for term in chunk]
        label = f"consolidate-{dimension}-chunk-{index}-of-{len(chunks)}"
        user_prompt = (
            f"DIMENSION: {dimension}\n"
            + ("ALLOWED TECHNOLOGY KINDS:\n" + kinds_json + "\n\n" if dimension == "technologies" else "")
            + "Consolidate this candidate chunk. Evidence has already been validated; preserve provenance using source_ids only.\n\n"
            + json.dumps({"candidates": compact}, indent=2, ensure_ascii=False)
        )
        result = cached_deepseek_json(
            root=root,
            cache_dir=cache_dir,
            use_cache=use_cache,
            refresh_cache=refresh_cache,
            api_key=api_key,
            model=chunk_model,
            system_prompt=CHUNK_CONSOLIDATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            label=label,
        )
        allowed = {source_id for item in compact for source_id in item["source_ids"]}
        clean = validate_consolidated_dimension_response(
            result,
            dimension=dimension,
            allowed_source_ids=allowed,
            allow_parent=False,
        )
        intermediate.extend(clean.values())
        print(f"  {dimension} chunk {index}/{len(chunks)} -> {len(clean)} term(s)", flush=True)

    intermediate = _deterministic_merge_consolidated_terms(intermediate)
    print(
        f"  {dimension}: {len(intermediate)} intermediate term(s) after deterministic merge",
        flush=True,
    )

    # A single chunk has already seen all candidates, so another AI call is not
    # required unless deterministic merging somehow changed the set materially.
    if len(chunks) == 1:
        final_with_sources = {term["id"]: term for term in intermediate}
    else:
        final_input = [_candidate_for_consolidation(term) for term in intermediate]
        label = f"reconcile-{dimension}-final"
        user_prompt = (
            f"DIMENSION: {dimension}\n"
            + ("ALLOWED TECHNOLOGY KINDS:\n" + kinds_json + "\n\n" if dimension == "technologies" else "")
            + "Reconcile these already-reduced terms across chunk boundaries.\n\n"
            + json.dumps({"terms": final_input}, indent=2, ensure_ascii=False)
        )
        result = cached_deepseek_json(
            root=root,
            cache_dir=cache_dir,
            use_cache=use_cache,
            refresh_cache=refresh_cache,
            api_key=api_key,
            model=final_model,
            system_prompt=FINAL_RECONCILIATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            label=label,
        )
        final_with_sources = validate_consolidated_dimension_response(
            result,
            dimension=dimension,
            allowed_source_ids=original_ids,
            allow_parent=True,
        )
        print(f"  {dimension}: final reconciliation -> {len(final_with_sources)} term(s)", flush=True)

    final_terms: dict[str, dict[str, Any]] = {}
    final_evidence: dict[str, list[dict[str, str]]] = {}
    for term_id, term in final_with_sources.items():
        evidence: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for source_id in term["source_ids"]:
            source = original_by_id.get(source_id)
            if source is None:
                continue
            for item in source.get("evidence", []):
                marker = (item["file"], item["reason"])
                if marker not in seen:
                    evidence.append({"file": item["file"], "reason": item["reason"]})
                    seen.add(marker)
        if not evidence:
            raise ValueError(f"Final term {dimension}.{term_id} resolved to no deterministic evidence")

        clean_term = {key: value for key, value in term.items() if key not in {"id", "source_ids"}}
        final_terms[term_id] = clean_term
        final_evidence[term_id] = evidence

    return final_terms, final_evidence


def write_generation_checkpoint(
    path: Path,
    *,
    generator: dict[str, Any],
    merged: dict[str, list[dict[str, Any]]],
    coverage_additions: list[dict[str, Any]],
    coverage_warnings: list[dict[str, Any]],
    rejected_technologies: list[dict[str, str]],
    per_document_technology_counts: dict[str, int],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generator": generator,
        "per_document_technology_counts": per_document_technology_counts,
        "candidate_counts": candidate_counts(merged),
        "coverage_audit_additions": coverage_additions,
        "coverage_warnings": coverage_warnings,
        "rejected_technology_candidates": rejected_technologies,
        "candidates": merged,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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
                signals = organisation_like_signals(description)
                if signals:
                    raise ValueError(
                        f"Final technology {term_id!r} looks organisation-like "
                        f"({', '.join(signals)})"
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


def restore_foundational_candidates(
    final_terms: dict[str, dict[str, Any]],
    final_evidence: dict[str, Any],
    merged_candidates: dict[str, list[dict[str, Any]]],
) -> list[dict[str, str]]:
    restored: list[dict[str, str]] = []
    tech_terms = final_terms["technologies"]
    tech_evidence = final_evidence["technologies"]

    for candidate in merged_candidates["technologies"]:
        if candidate.get("kind") not in FOUNDATIONAL_PRESERVE_KINDS:
            continue
        if represented_by_terms(candidate, tech_terms):
            continue
        if organisation_like_signals(candidate["description"]):
            continue

        term_id = candidate["id"]
        if term_id in tech_terms:
            continue
        term: dict[str, Any] = {
            "label": candidate["label"],
            "description": candidate["description"],
            "kind": candidate["kind"],
        }
        if candidate.get("parent") and candidate["parent"] in tech_terms:
            term["parent"] = candidate["parent"]
        if candidate.get("aliases"):
            term["aliases"] = candidate["aliases"]
        tech_terms[term_id] = term
        tech_evidence[term_id] = candidate["evidence"]
        restored.append(
            {
                "id": term_id,
                "label": candidate["label"],
                "kind": candidate["kind"],
                "reason": "Validated foundational candidate restored after consolidation omitted it.",
            }
        )
    return restored


def deterministic_coverage_warnings(
    documents: list[dict[str, str]],
    candidates: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    terms = {term["id"]: term for term in candidates["technologies"]}

    for expected_id, spec in FOUNDATIONAL_COVERAGE_PATTERNS.items():
        probe = {"id": expected_id, "label": spec["label"], "aliases": []}
        if represented_by_terms(probe, terms):
            continue

        files: list[str] = []
        occurrences = 0
        compiled = [re.compile(pattern, re.IGNORECASE) for pattern in spec["patterns"]]
        for document in documents:
            document_count = sum(len(pattern.findall(document["content"])) for pattern in compiled)
            if document_count:
                files.append(document["file"])
                occurrences += document_count
        if files:
            warnings.append(
                {
                    "expected_id": expected_id,
                    "label": spec["label"],
                    "kind": spec["kind"],
                    "occurrences": occurrences,
                    "files": files,
                    "reason": (
                        "Foundational technology text occurs in the corpus but no extracted "
                        "candidate resolves to this ID/label. Review for an extraction false negative."
                    ),
                }
            )
    return warnings


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

    if args.model:
        extraction_model = args.model
        coverage_model = args.model
        chunk_consolidation_model = args.model
        consolidation_model = args.model
    else:
        extraction_model = args.extraction_model
        coverage_model = args.coverage_model
        chunk_consolidation_model = args.chunk_consolidation_model
        consolidation_model = args.consolidation_model

    cache_dir = args.cache_dir
    use_cache = not args.no_cache

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
    kinds_json = technology_kinds_prompt()

    print(f"found {len(documents)} Markdown/MDX files in {len(batches)} non-technology batch(es)")

    candidate_sets: list[dict[str, list[dict[str, Any]]]] = []
    rejected_technologies: list[dict[str, str]] = []

    # Pass 1: content types, audiences and topics in normal repository batches.
    for index, batch in enumerate(batches, start=1):
        batch_files = {document["file"] for document in batch}
        print(f"extracting non-technology candidates {index}/{len(batches)} ({len(batch)} files)")
        result = cached_deepseek_json(
            root=root,
            cache_dir=cache_dir,
            use_cache=use_cache,
            refresh_cache=args.refresh_cache,
            api_key=api_key,
            model=extraction_model,
            system_prompt=NONTECH_EXTRACTION_SYSTEM_PROMPT,
            user_prompt=(
                "Analyse these repository documents and return controlled-vocabulary candidates.\n\n"
                + "\n\n".join(format_document(document) for document in batch)
            ),
            max_tokens=args.max_tokens,
            timeout_seconds=args.request_timeout,
            label=f"extract-nontech-{index}-of-{len(batches)}",
        )
        validated = validate_nontech_response(result, batch_files)
        candidate_sets.append(validated)
        print(
            "  "
            + ", ".join(
                f"{dimension}={len(validated[dimension])}"
                for dimension in ("content_types", "audiences", "topics")
            )
        )

    # Pass 2: technology extraction, deliberately one document at a time.
    per_document_technology_counts: dict[str, int] = {}
    for index, document in enumerate(documents, start=1):
        print(f"extracting technologies {index}/{len(documents)}: {document['file']}")
        result = cached_deepseek_json(
            root=root,
            cache_dir=cache_dir,
            use_cache=use_cache,
            refresh_cache=args.refresh_cache,
            api_key=api_key,
            model=extraction_model,
            system_prompt=TECHNOLOGY_EXTRACTION_SYSTEM_PROMPT,
            user_prompt=(
                "ALLOWED TECHNOLOGY KINDS:\n"
                + kinds_json
                + "\n\nExtract all materially supported technologies from this document.\n\n"
                + format_document(document)
            ),
            max_tokens=args.max_tokens,
            timeout_seconds=args.request_timeout,
            label=f"extract-tech-{index:03d}-{Path(document['file']).stem}",
        )
        technologies, rejected = validate_technology_response(result, {document["file"]})
        per_document_technology_counts[document["file"]] = len(technologies)
        for item in rejected:
            rejected_technologies.append({"file": document["file"], **item})
        candidate_sets.append(
            {
                "content_types": [],
                "audiences": [],
                "topics": [],
                "technologies": technologies,
            }
        )
        print(f"  technologies={len(technologies)}")

    merged = merge_candidates(candidate_sets)
    print(
        "merged candidates before coverage audit: "
        + ", ".join(f"{key}={value}" for key, value in candidate_counts(merged).items())
    )

    # Pass 3: coverage audit. Give the model the existing inventory and ask only
    # for genuinely missing technologies from each repository batch.
    coverage_additions: list[dict[str, Any]] = []
    if not args.skip_coverage_audit:
        for index, batch in enumerate(batches, start=1):
            print(f"auditing technology coverage {index}/{len(batches)} ({len(batch)} files)")
            inventory = [
                {
                    "id": term["id"],
                    "label": term["label"],
                    "kind": term["kind"],
                    "aliases": term.get("aliases", []),
                }
                for term in merged["technologies"]
            ]
            result = cached_deepseek_json(
                root=root,
                cache_dir=cache_dir,
                use_cache=use_cache,
                refresh_cache=args.refresh_cache,
                api_key=api_key,
                model=coverage_model,
                system_prompt=COVERAGE_AUDIT_SYSTEM_PROMPT,
                user_prompt=(
                    "ALLOWED TECHNOLOGY KINDS:\n"
                    + kinds_json
                    + "\n\nEXISTING TECHNOLOGY CANDIDATES:\n"
                    + json.dumps(inventory, indent=2, ensure_ascii=False)
                    + "\n\nSOURCE DOCUMENTS:\n\n"
                    + "\n\n".join(format_document(document) for document in batch)
                ),
                max_tokens=args.max_tokens,
                timeout_seconds=args.request_timeout,
                label=f"coverage-audit-{index}-of-{len(batches)}",
            )
            additions, rejected = validate_technology_response(
                result, {document["file"] for document in batch}
            )
            for item in rejected:
                rejected_technologies.append({"file": "<coverage-audit>", **item})
            if additions:
                coverage_additions.extend(additions)
                merged = merge_candidates(
                    [
                        merged,
                        {
                            "content_types": [],
                            "audiences": [],
                            "topics": [],
                            "technologies": additions,
                        },
                    ]
                )
            print(f"  missing technologies added={len(additions)}")

    coverage_warnings = deterministic_coverage_warnings(documents, merged)
    for warning in coverage_warnings:
        print(
            f"COVERAGE WARNING: {warning['label']} occurs {warning['occurrences']} time(s) "
            f"in {len(warning['files'])} file(s) but no candidate resolves to it",
            file=sys.stderr,
        )

    print(
        "merged candidates after coverage audit: "
        + ", ".join(f"{key}={value}" for key, value in candidate_counts(merged).items())
    )

    checkpoint_output = root / DEFAULT_CHECKPOINT_OUTPUT
    generator_checkpoint = {
        "taxonomy_version": taxonomy_tools.TAXONOMY_VERSION,
        "extraction_model": extraction_model,
        "coverage_model": coverage_model,
        "chunk_consolidation_model": chunk_consolidation_model,
        "consolidation_model": consolidation_model,
        "introduced_date": args.introduced_date,
        "source_file_count": len(documents),
        "nontechnology_batch_count": len(batches),
        "technology_extraction_mode": "per-document-high-recall",
        "coverage_audit_enabled": not args.skip_coverage_audit,
        "cache_enabled": use_cache,
        "cache_dir": str(cache_dir),
        "consolidation_chunk_size": args.consolidation_chunk_size,
    }
    write_generation_checkpoint(
        checkpoint_output,
        generator=generator_checkpoint,
        merged=merged,
        coverage_additions=coverage_additions,
        coverage_warnings=coverage_warnings,
        rejected_technologies=rejected_technologies,
        per_document_technology_counts=per_document_technology_counts,
    )
    print(f"wrote checkpoint {checkpoint_output.relative_to(root).as_posix()}", flush=True)
    print("consolidating taxonomy by dimension and chunk", flush=True)

    final_terms: dict[str, dict[str, Any]] = {}
    final_evidence: dict[str, Any] = {}
    for dimension in ("content_types", "audiences", "topics", "technologies"):
        terms, evidence = consolidate_dimension(
            root=root,
            dimension=dimension,
            candidates=merged[dimension],
            api_key=api_key,
            kinds_json=kinds_json,
            chunk_model=chunk_consolidation_model,
            final_model=consolidation_model,
            chunk_size=args.consolidation_chunk_size,
            max_tokens=args.max_tokens,
            timeout_seconds=args.request_timeout,
            cache_dir=cache_dir,
            use_cache=use_cache,
            refresh_cache=args.refresh_cache,
        )
        final_terms[dimension] = terms
        final_evidence[dimension] = evidence

    restored_foundational = restore_foundational_candidates(
        final_terms, final_evidence, merged
    )
    if restored_foundational:
        print(
            f"restored {len(restored_foundational)} foundational technology candidate(s) "
            "that consolidation omitted"
        )

    taxonomy = build_taxonomy(final_terms, args.introduced_date)
    taxonomy_tools.validate_taxonomy_schema(taxonomy, root / taxonomy_tools.SCHEMA_PATH)
    taxonomy_tools.validate_taxonomy_semantics(taxonomy)
    write_yaml(output, taxonomy)
    taxonomy_tools.generate_derived_files(root, taxonomy)

    audit = {
        "generator": {
            "taxonomy_version": taxonomy_tools.TAXONOMY_VERSION,
            "extraction_model": extraction_model,
            "coverage_model": coverage_model,
            "chunk_consolidation_model": chunk_consolidation_model,
            "consolidation_model": consolidation_model,
            "introduced_date": args.introduced_date,
            "source_file_count": len(documents),
            "nontechnology_batch_count": len(batches),
            "technology_extraction_mode": "per-document-high-recall",
            "coverage_audit_enabled": not args.skip_coverage_audit,
            "cache_enabled": use_cache,
            "cache_dir": str(cache_dir),
            "consolidation_chunk_size": args.consolidation_chunk_size,
            "checkpoint": DEFAULT_CHECKPOINT_OUTPUT.as_posix(),
        },
        "technology_kinds": taxonomy_tools.DEFAULT_TECHNOLOGY_KINDS,
        "source_files": sorted(known_files),
        "per_document_technology_counts": per_document_technology_counts,
        "candidate_counts": candidate_counts(merged),
        "final_counts": {
            dimension: len(final_terms[dimension]) for dimension in DISCOVERED_DIMENSIONS
        },
        "coverage_audit_additions": coverage_additions,
        "coverage_warnings": coverage_warnings,
        "rejected_technology_candidates": rejected_technologies,
        "restored_foundational_candidates": restored_foundational,
        "candidates": merged,
        "evidence": final_evidence,
    }
    audit_output.parent.mkdir(parents=True, exist_ok=True)
    audit_output.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"wrote {output.relative_to(root).as_posix()}")
    print(f"wrote {audit_output.relative_to(root).as_posix()}")
    print("review the taxonomy before running taxonomy_ai.py --all --apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
