#!/usr/bin/env python3
"""Deterministic taxonomy, front-matter, and derived-file tooling.

Taxonomy v2 adds typed technology subclasses and optional content-type-specific
cardinality constraints while keeping the public front matter simple. All governed
taxonomy dimensions are serialised as YAML lists, including dimensions whose
maximum cardinality is one:

  type:
    - case-study
  technologies:
    - python
    - openapi
    - docusaurus
  lifecycle:
    - current

The canonical taxonomy is taxonomy/taxonomy.yml. This script never calls an
LLM, so it is safe to use as a blocking CI check.

Commands:

  python scripts/taxonomy.py generate
  python scripts/taxonomy.py check --all
  python scripts/taxonomy.py check --changed-base <git-sha>
  python scripts/taxonomy.py check docs/example.md
  python scripts/taxonomy.py sync --all
  python scripts/taxonomy.py audit-technologies

`generate` writes files derived from the canonical taxonomy:

  docs/tags.yml
  .frontmatter/generated-taxonomy.json

`check` validates the taxonomy itself, confirms derived files are in sync, and
optionally validates document front matter.

`sync` synchronises the Docusaurus `tags` field from governed dimensions whose
`docusaurus_tags` flag is true. It never chooses taxonomy values.

`audit-technologies` groups technology terms by kind and emits non-blocking
warnings for descriptions that look organisation-like. Use --strict to turn
those warnings into a non-zero exit code.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

import jsonschema
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap


TAXONOMY_VERSION = 2
TAXONOMY_PATH = Path("taxonomy/taxonomy.yml")
SCHEMA_PATH = Path("taxonomy/schema.json")
DOCUSAURUS_TAGS_PATH = Path("docs/tags.yml")
FRONTMATTER_PROJECTION_PATH = Path(".frontmatter/generated-taxonomy.json")

DOC_SUFFIXES = {".md", ".mdx"}
TERM_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

REQUIRED_DIMENSIONS = {
    "content_types",
    "audiences",
    "topics",
    "technologies",
    "lifecycle",
}

ALLOWED_GOVERNANCE_SOURCES = {
    "initial-taxonomy",
    "ai-proposed",
    "human-proposed",
    "policy-seeded",
    "migration",
}

# Seed catalogue used only when creating/upgrading a taxonomy. Once written,
# taxonomy/taxonomy.yml is authoritative. These are intentionally broad enough
# to cover a long technical-writing/programming career without treating
# companies, employers, clients, or customers as technologies.
DEFAULT_TECHNOLOGY_KINDS: dict[str, dict[str, str]] = {
    "programming-language": {
        "label": "Programming language",
        "description": "A general-purpose or domain-specific programming language.",
    },
    "shell-scripting": {
        "label": "Shell and scripting",
        "description": "A shell, command language, or scripting environment used for automation.",
    },
    "markup-content-language": {
        "label": "Markup and content language",
        "description": "A markup, content, or document syntax used to author structured text.",
    },
    "data-format": {
        "label": "Data format",
        "description": "A structured data serialisation or interchange format such as JSON, YAML, or XML.",
    },
    "framework": {
        "label": "Framework",
        "description": "A software framework that provides reusable structure for applications or tooling.",
    },
    "library": {
        "label": "Library",
        "description": "A reusable software library or package.",
    },
    "runtime": {
        "label": "Runtime",
        "description": "A runtime environment used to execute software.",
    },
    "standard-specification": {
        "label": "Standard or specification",
        "description": "A formal technical standard, specification, or interoperable data definition.",
    },
    "protocol": {
        "label": "Protocol",
        "description": "A technical communication, security, or directory protocol.",
    },
    "api-tool": {
        "label": "API tool",
        "description": "A tool used to design, document, test, inspect, or work with APIs.",
    },
    "payment-technology": {
        "label": "Payment technology",
        "description": "A payment-specific technical product, wallet integration, tokenisation technology, checkout technology, or payment platform used in implementation work.",
    },
    "documentation-platform": {
        "label": "Documentation platform",
        "description": "A documentation site generator or platform used to publish technical content.",
    },
    "authoring-tool": {
        "label": "Authoring tool",
        "description": "A specialised application used to author or manage technical documentation.",
    },
    "documentation-qa-tool": {
        "label": "Documentation QA tool",
        "description": "A deterministic spelling, grammar, prose, style, or documentation-quality tool.",
    },
    "cms-wiki": {
        "label": "CMS or wiki",
        "description": "A content-management or wiki platform used to create and maintain content.",
    },
    "developer-platform": {
        "label": "Developer platform",
        "description": "A hosted or local platform that supports software development workflows.",
    },
    "developer-tool": {
        "label": "Developer tool",
        "description": "A general-purpose software-development tool not better represented by another kind.",
    },
    "ide-editor": {
        "label": "IDE or editor",
        "description": "An integrated development environment or source-code editor.",
    },
    "testing-debugging-tool": {
        "label": "Testing or debugging tool",
        "description": "A tool used to test, debug, inspect, or diagnose software systems.",
    },
    "network-analysis-tool": {
        "label": "Network analysis tool",
        "description": "A tool used to inspect, capture, or analyse network traffic and protocols.",
    },
    "ci-cd-automation": {
        "label": "CI/CD and automation",
        "description": "A continuous-integration, delivery, deployment, or build-automation technology.",
    },
    "version-control": {
        "label": "Version control",
        "description": "A version-control technology or source-management system.",
    },
    "container-platform": {
        "label": "Container and orchestration platform",
        "description": "A containerisation, orchestration, or workload-management platform.",
    },
    "infrastructure-platform": {
        "label": "Infrastructure platform",
        "description": "A virtualisation, infrastructure, or systems-management platform.",
    },
    "operating-system-firmware": {
        "label": "Operating system or firmware",
        "description": "An operating system, operating-system family, or device firmware platform.",
    },
    "server-networking": {
        "label": "Server and networking software",
        "description": "A web server, application server, reverse proxy, or related networking technology.",
    },
    "cloud-hosting-platform": {
        "label": "Cloud or hosting platform",
        "description": "A hosted development, deployment, or static-site platform.",
    },
    "diagramming-visualisation": {
        "label": "Diagramming and visualisation",
        "description": "A tool or language used to create diagrams, charts, or technical visualisations.",
    },
    "modelling-methodology": {
        "label": "Modelling methodology",
        "description": "A technical modelling notation, method, or structured architecture-modelling approach.",
    },
    "architecture-style": {
        "label": "Architecture style",
        "description": "A reusable software or systems architecture style used in technical work.",
    },
    "technical-technique": {
        "label": "Technical technique",
        "description": "A reusable technical technique or capability that is materially demonstrated.",
    },
    "security-cryptography": {
        "label": "Security and cryptography",
        "description": "A security, cryptography, identity, or trust technology not better represented as a protocol.",
    },
    "ai-ml-tool": {
        "label": "AI or ML tool",
        "description": "An AI/ML model, assistant, API, platform, or development tool.",
    },
    "data-analysis-tool": {
        "label": "Data and analysis tool",
        "description": "A data-processing, analysis, search, indexing, or data-oriented technology.",
    },
    "design-graphics-tool": {
        "label": "Design and graphics tool",
        "description": "A graphics, illustration, or visual-design application used in technical work.",
    },
    "engineering-design-tool": {
        "label": "Engineering design tool",
        "description": "A CAD, engineering, or product-design application.",
    },
    "collaboration-project-tool": {
        "label": "Collaboration and project tool",
        "description": "A collaboration, annotation, issue-tracking, or project-management tool.",
    },
    "software-platform": {
        "label": "Software platform",
        "description": "A reusable software product or application platform not better represented by another kind.",
    },
}

# Content-type overrides keep individual pages selective while allowing the
# overall career taxonomy to contain hundreds of terms if evidence supports it.
DEFAULT_TECHNOLOGY_CONSTRAINTS_BY_TYPE: dict[str, dict[str, int]] = {
    "case-study": {"min": 0, "max": 15},
    "skill": {"min": 0, "max": 20},
    "tool": {"min": 0, "max": 40},
}

# Heuristic only: these warnings do not replace human review or kind validation.
ORGANISATION_LIKE_DESCRIPTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("company", re.compile(r"\bcompany\b", re.IGNORECASE)),
    ("corporation", re.compile(r"\bcorporation\b", re.IGNORECASE)),
    ("firm", re.compile(r"\b(?:financial services |consulting |investment )?firm\b", re.IGNORECASE)),
    ("manufacturer", re.compile(r"\bmanufacturer\b", re.IGNORECASE)),
    ("bank", re.compile(r"\b(?:bank|banking institution|financial institution)\b", re.IGNORECASE)),
    ("employer/client", re.compile(r"\b(?:employer|client|customer)\b", re.IGNORECASE)),
    ("provider", re.compile(r"\b(?:payment|wallet|financial|banking)\b.*\bprovider\b", re.IGNORECASE)),
)


class ValidationError(Exception):
    """A deterministic validation error suitable for CI output."""


def safe_yaml() -> YAML:
    yaml = YAML(typ="safe")
    yaml.default_flow_style = False
    return yaml


def round_trip_yaml() -> YAML:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 100
    return yaml


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValidationError(
            f"{path} does not exist. Run `python scripts/generate_taxonomy.py` "
            "to create the initial taxonomy."
        )
    with path.open("r", encoding="utf-8") as handle:
        data = safe_yaml().load(handle)
    if not isinstance(data, dict):
        raise ValidationError(f"{path} must contain a YAML object at its root.")
    return data


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValidationError(f"{path} does not exist.")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValidationError(f"{path} must contain a JSON object at its root.")
    return data


def validate_taxonomy_schema(taxonomy: dict[str, Any], schema_path: Path) -> None:
    schema = load_json(schema_path)
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(taxonomy), key=lambda error: list(error.path))
    if not errors:
        return
    rendered = []
    for error in errors:
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        rendered.append(f"taxonomy schema: {location}: {error.message}")
    raise ValidationError("\n".join(rendered))


def active_terms(dimension: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        term_id: term
        for term_id, term in dimension.get("terms", {}).items()
        if term.get("governance", {}).get("status") == "active"
    }


def technology_kind_ids(taxonomy: dict[str, Any]) -> set[str]:
    return set(taxonomy.get("technology_kinds", {}))


def effective_limits(
    dimension: dict[str, Any],
    content_type: str | None,
) -> tuple[int, int]:
    minimum = dimension["min"]
    maximum = dimension["max"]
    constraints = dimension.get("constraints_by_type", {})
    if content_type and isinstance(constraints, dict):
        override = constraints.get(content_type)
        if isinstance(override, dict):
            minimum = override.get("min", minimum)
            maximum = override.get("max", maximum)
    return minimum, maximum


def validate_taxonomy_semantics(taxonomy: dict[str, Any]) -> None:
    if taxonomy.get("version") != TAXONOMY_VERSION:
        raise ValidationError(
            f"taxonomy version must be {TAXONOMY_VERSION}; "
            "run `python scripts/upgrade_taxonomy.py` for a v1 taxonomy"
        )

    dimensions = taxonomy.get("dimensions", {})
    missing = REQUIRED_DIMENSIONS - set(dimensions)
    unexpected = set(dimensions) - REQUIRED_DIMENSIONS
    if missing:
        raise ValidationError("taxonomy is missing required dimensions: " + ", ".join(sorted(missing)))
    if unexpected:
        raise ValidationError("taxonomy contains unsupported dimensions: " + ", ".join(sorted(unexpected)))

    technology_kinds = taxonomy.get("technology_kinds")
    if not isinstance(technology_kinds, dict) or not technology_kinds:
        raise ValidationError("taxonomy must define a non-empty technology_kinds catalogue")
    for kind_id, kind in technology_kinds.items():
        if not TERM_ID_RE.fullmatch(kind_id):
            raise ValidationError(f"technology kind {kind_id!r} must be lower-case kebab-case")
        if not isinstance(kind, dict):
            raise ValidationError(f"technology kind {kind_id!r} must be an object")
        if not str(kind.get("label", "")).strip() or not str(kind.get("description", "")).strip():
            raise ValidationError(f"technology kind {kind_id!r} needs label and description")

    seen_metadata_fields: dict[str, str] = {}
    visible_tag_ids: dict[str, str] = {}

    for dimension_id, dimension in dimensions.items():
        metadata_field = dimension["metadata_field"]
        if metadata_field in seen_metadata_fields:
            raise ValidationError(
                f"metadata field {metadata_field!r} is shared by "
                f"{seen_metadata_fields[metadata_field]!r} and {dimension_id!r}"
            )
        seen_metadata_fields[metadata_field] = dimension_id

        minimum = dimension["min"]
        maximum = dimension["max"]
        multiple = dimension["multiple"]
        if minimum > maximum:
            raise ValidationError(f"{dimension_id}: min cannot be greater than max")
        if not multiple and maximum != 1:
            raise ValidationError(f"{dimension_id}: a single-value dimension must have max: 1")

        constraints = dimension.get("constraints_by_type", {})
        if constraints:
            if not isinstance(constraints, dict):
                raise ValidationError(f"{dimension_id}: constraints_by_type must be an object")
            content_type_terms = dimensions["content_types"]["terms"]
            for type_id, override in constraints.items():
                if type_id not in content_type_terms:
                    raise ValidationError(
                        f"{dimension_id}: constraints_by_type references unknown content type {type_id!r}"
                    )
                if not isinstance(override, dict):
                    raise ValidationError(
                        f"{dimension_id}: constraint for {type_id!r} must be an object"
                    )
                override_min = override.get("min", minimum)
                override_max = override.get("max", maximum)
                if override_min < 0 or override_max < 1 or override_min > override_max:
                    raise ValidationError(
                        f"{dimension_id}: invalid cardinality override for {type_id!r}"
                    )
                if not multiple and override_max != 1:
                    raise ValidationError(
                        f"{dimension_id}: single-value constraint for {type_id!r} must have max: 1"
                    )

        terms = dimension["terms"]
        if dimension["required"] and dimension["min"] > 0 and not active_terms(dimension):
            raise ValidationError(f"{dimension_id}: required dimension has no active terms")

        lower_labels: dict[str, str] = {}
        lower_aliases: dict[str, str] = {}

        for term_id, term in terms.items():
            if not TERM_ID_RE.fullmatch(term_id):
                raise ValidationError(f"{dimension_id}.{term_id}: IDs must be lower-case kebab-case")

            governance = term["governance"]
            source = governance["source"]
            if source not in ALLOWED_GOVERNANCE_SOURCES:
                raise ValidationError(
                    f"{dimension_id}.{term_id}: unsupported governance source {source!r}"
                )
            introduced = governance["introduced"]
            if not isinstance(introduced, str) or not DATE_RE.fullmatch(introduced):
                raise ValidationError(
                    f"{dimension_id}.{term_id}: governance.introduced must be YYYY-MM-DD"
                )

            status = governance["status"]
            replaced_by = governance.get("replaced_by")
            if status == "active" and replaced_by:
                raise ValidationError(f"{dimension_id}.{term_id}: active terms cannot have replaced_by")
            if replaced_by:
                if replaced_by == term_id:
                    raise ValidationError(f"{dimension_id}.{term_id}: replaced_by cannot refer to itself")
                if replaced_by not in terms:
                    raise ValidationError(
                        f"{dimension_id}.{term_id}: replaced_by {replaced_by!r} does not exist"
                    )
                if terms[replaced_by]["governance"]["status"] != "active":
                    raise ValidationError(
                        f"{dimension_id}.{term_id}: replacement {replaced_by!r} must be active"
                    )

            if dimension_id == "technologies" and status == "active":
                kind = term.get("kind")
                if not isinstance(kind, str) or not kind:
                    raise ValidationError(
                        f"technologies.{term_id}: active technology terms require a kind"
                    )
                if kind not in technology_kinds:
                    raise ValidationError(
                        f"technologies.{term_id}: unknown technology kind {kind!r}"
                    )
            elif dimension_id != "technologies" and "kind" in term:
                raise ValidationError(
                    f"{dimension_id}.{term_id}: kind is only valid for technology terms"
                )

            label_key = term["label"].strip().casefold()
            if label_key in lower_labels:
                raise ValidationError(
                    f"{dimension_id}: duplicate labels for {lower_labels[label_key]!r} and {term_id!r}"
                )
            lower_labels[label_key] = term_id

            for alias in term.get("aliases", []):
                alias_key = alias.strip().casefold()
                if alias_key == label_key:
                    raise ValidationError(
                        f"{dimension_id}.{term_id}: alias duplicates its label: {alias!r}"
                    )
                if alias_key in lower_aliases and lower_aliases[alias_key] != term_id:
                    raise ValidationError(
                        f"{dimension_id}: alias {alias!r} is shared by "
                        f"{lower_aliases[alias_key]!r} and {term_id!r}"
                    )
                lower_aliases[alias_key] = term_id

            parent = term.get("parent")
            if parent:
                if parent == term_id:
                    raise ValidationError(f"{dimension_id}.{term_id}: term cannot parent itself")
                if parent not in terms:
                    raise ValidationError(
                        f"{dimension_id}.{term_id}: parent {parent!r} does not exist"
                    )
                if status == "active" and terms[parent]["governance"]["status"] != "active":
                    raise ValidationError(
                        f"{dimension_id}.{term_id}: active terms cannot use deprecated parent {parent!r}"
                    )

            if dimension.get("docusaurus_tags") and status == "active":
                previous_dimension = visible_tag_ids.get(term_id)
                if previous_dimension:
                    raise ValidationError(
                        f"Docusaurus tag ID {term_id!r} is present in both "
                        f"{previous_dimension!r} and {dimension_id!r}. Visible tag IDs must be globally unique."
                    )
                visible_tag_ids[term_id] = dimension_id

        for alias_key, alias_term in lower_aliases.items():
            label_term = lower_labels.get(alias_key)
            if label_term and label_term != alias_term:
                raise ValidationError(
                    f"{dimension_id}: alias on {alias_term!r} duplicates label on {label_term!r}"
                )

        # Detect parent cycles and keep the vocabulary intentionally shallow.
        for term_id in terms:
            chain: list[str] = []
            current = term_id
            while current:
                if current in chain:
                    raise ValidationError(
                        f"{dimension_id}: parent cycle detected: " + " -> ".join(chain + [current])
                    )
                chain.append(current)
                parent = terms[current].get("parent")
                if not parent:
                    break
                current = parent
            if len(chain) > 3:
                raise ValidationError(
                    f"{dimension_id}.{term_id}: taxonomy hierarchy is deeper than two parents"
                )

    lifecycle = dimensions["lifecycle"]
    if lifecycle.get("ai_managed"):
        raise ValidationError("lifecycle must set ai_managed: false")


def load_and_validate_taxonomy(root: Path) -> dict[str, Any]:
    taxonomy = load_yaml(root / TAXONOMY_PATH)
    validate_taxonomy_schema(taxonomy, root / SCHEMA_PATH)
    validate_taxonomy_semantics(taxonomy)
    return taxonomy


def render_docusaurus_tags(taxonomy: dict[str, Any]) -> str:
    tags: dict[str, dict[str, str]] = {}
    for dimension in taxonomy["dimensions"].values():
        if not dimension.get("docusaurus_tags"):
            continue
        for term_id, term in active_terms(dimension).items():
            tags[term_id] = {
                "label": term["label"],
                "description": term["description"],
            }

    stream = io.StringIO()
    yaml = safe_yaml()
    yaml.width = 100
    yaml.dump(dict(sorted(tags.items())), stream)
    return (
        "# AUTO-GENERATED FROM taxonomy/taxonomy.yml.\n"
        "# Do not edit this file directly; run `python scripts/taxonomy.py generate`.\n\n"
        + stream.getvalue()
    )


def taxonomy_field_definition(
    dimension_id: str,
    dimension: dict[str, Any],
    *,
    content_type: str | None = None,
) -> dict[str, Any]:
    minimum, maximum = effective_limits(dimension, content_type)

    field: dict[str, Any] = {
        "title": dimension_id.replace("_", " ").title(),
        "name": dimension["metadata_field"],
        "type": "taxonomy",
        "taxonomyId": dimension_id,
        "required": dimension["required"] or minimum > 0,
        # Cardinality and YAML serialisation are separate concerns. Front Matter
        # may allow only one selection, but governed taxonomy metadata is always
        # stored as a YAML list.
        "taxonomyLimit": maximum,
        "singleValueAsString": False,
    }

    return field


def common_frontmatter_fields() -> list[dict[str, Any]]:
    return [
        {"title": "Title", "name": "title", "type": "string", "required": True},
        {"title": "Description", "name": "description", "type": "string", "required": False},
        {"title": "Slug", "name": "slug", "type": "slug", "required": False},
        {
            "title": "Sidebar position",
            "name": "sidebar_position",
            "type": "number",
            "required": False,
        },
    ]


def fields_for_content_type(
    taxonomy: dict[str, Any],
    content_type: str | None,
) -> list[dict[str, Any]]:
    dimensions = taxonomy["dimensions"]
    fields = common_frontmatter_fields()
    for dimension_id in ["content_types", "audiences", "topics", "technologies", "lifecycle"]:
        fields.append(
            taxonomy_field_definition(
                dimension_id,
                dimensions[dimension_id],
                content_type=content_type,
            )
        )
    fields.append(
        {
            "title": "Docusaurus tags (derived)",
            "name": "tags",
            "type": "list",
            "hidden": True,
            "required": False,
        }
    )
    return fields


def build_frontmatter_projection(taxonomy: dict[str, Any]) -> dict[str, Any]:
    dimensions = taxonomy["dimensions"]

    custom_taxonomy = []
    for dimension_id, dimension in dimensions.items():
        custom_taxonomy.append(
            {
                "id": dimension_id,
                "options": sorted(active_terms(dimension).keys()),
            }
        )

    content_type_ids = sorted(active_terms(dimensions["content_types"]).keys())
    content_types = [
        {
            "name": "default",
            "pageBundle": False,
            "fields": fields_for_content_type(taxonomy, None),
        }
    ]
    for content_type_id in content_type_ids:
        content_types.append(
            {
                "name": content_type_id,
                "pageBundle": False,
                "fields": fields_for_content_type(taxonomy, content_type_id),
            }
        )

    docusaurus_tags = []
    for dimension in dimensions.values():
        if dimension.get("docusaurus_tags"):
            docusaurus_tags.extend(active_terms(dimension).keys())

    technology_terms_by_kind: dict[str, list[str]] = {
        kind_id: [] for kind_id in taxonomy["technology_kinds"]
    }
    for term_id, term in active_terms(dimensions["technologies"]).items():
        technology_terms_by_kind.setdefault(term["kind"], []).append(term_id)
    for kind_id in technology_terms_by_kind:
        technology_terms_by_kind[kind_id] = sorted(technology_terms_by_kind[kind_id])

    return {
        "generatedFrom": TAXONOMY_PATH.as_posix(),
        "taxonomyVersion": taxonomy["version"],
        "customTaxonomy": custom_taxonomy,
        "contentTypes": content_types,
        "docusaurusTags": sorted(set(docusaurus_tags)),
        "technologyKinds": taxonomy["technology_kinds"],
        "technologyTermsByKind": technology_terms_by_kind,
    }


def render_frontmatter_projection(taxonomy: dict[str, Any]) -> str:
    return json.dumps(build_frontmatter_projection(taxonomy), indent=2, ensure_ascii=False) + "\n"


def expected_derived_files(taxonomy: dict[str, Any]) -> dict[Path, str]:
    return {
        DOCUSAURUS_TAGS_PATH: render_docusaurus_tags(taxonomy),
        FRONTMATTER_PROJECTION_PATH: render_frontmatter_projection(taxonomy),
    }


def generate_derived_files(root: Path, taxonomy: dict[str, Any]) -> None:
    for relative_path, content in expected_derived_files(taxonomy).items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"generated {relative_path.as_posix()}")


def check_derived_files(root: Path, taxonomy: dict[str, Any]) -> list[str]:
    errors = []
    for relative_path, expected in expected_derived_files(taxonomy).items():
        path = root / relative_path
        if not path.exists():
            errors.append(
                f"{relative_path}: missing generated file; run `python scripts/taxonomy.py generate`"
            )
            continue
        actual = path.read_text(encoding="utf-8")
        if actual != expected:
            errors.append(
                f"{relative_path}: out of sync with {TAXONOMY_PATH}; run "
                "`python scripts/taxonomy.py generate`"
            )
    return errors


def split_front_matter(text: str) -> tuple[str, str, str] | None:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None
    for index in range(1, len(lines)):
        if lines[index].strip() in {"---", "..."}:
            front = "".join(lines[1:index])
            body = "".join(lines[index + 1 :])
            return lines[0], front, body
    return None


def load_front_matter(path: Path) -> tuple[CommentedMap, str]:
    text = path.read_text(encoding="utf-8")
    split = split_front_matter(text)
    if split is None:
        raise ValidationError(f"{path}: missing YAML front matter")
    _, front_text, body = split
    yaml = round_trip_yaml()
    data = yaml.load(front_text)
    if data is None:
        data = CommentedMap()
    if not isinstance(data, CommentedMap):
        raise ValidationError(f"{path}: front matter root must be a YAML object")
    return data, body


def write_front_matter(path: Path, front_matter: CommentedMap, body: str) -> None:
    yaml = round_trip_yaml()
    stream = io.StringIO()
    yaml.dump(front_matter, stream)
    rendered = "---\n" + stream.getvalue() + "---\n" + body
    path.write_text(rendered, encoding="utf-8")


def value_as_list(value: Any) -> list[str] | None:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    return None


def validate_document_front_matter(
    path: Path,
    root: Path,
    taxonomy: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    relative = path.relative_to(root).as_posix()

    try:
        front_matter, _ = load_front_matter(path)
    except ValidationError as error:
        return [str(error).replace(str(root) + "/", "")]

    dimensions = taxonomy["dimensions"]
    selected: dict[str, list[str]] = {}

    content_type_value = front_matter.get(dimensions["content_types"]["metadata_field"])
    content_type = (
        content_type_value[0]
        if isinstance(content_type_value, list)
        and len(content_type_value) == 1
        and isinstance(content_type_value[0], str)
        else None
    )

    for dimension_id, dimension in dimensions.items():
        field_name = dimension["metadata_field"]
        value = front_matter.get(field_name)
        minimum, maximum = effective_limits(dimension, content_type)

        if value is None:
            if dimension["required"] or minimum > 0:
                errors.append(f"{relative}: required metadata field {field_name!r} is missing")
            selected[dimension_id] = []
            continue

        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            errors.append(
                f"{relative}: metadata field {field_name!r} must be a YAML list of taxonomy IDs"
            )
            selected[dimension_id] = []
            continue

        values = list(value)

        if len(values) < minimum or len(values) > maximum:
            suffix = f" for content type {content_type!r}" if content_type else ""
            errors.append(
                f"{relative}: metadata field {field_name!r} requires "
                f"{minimum}..{maximum} value(s){suffix}; found {len(values)}"
            )

        if len(values) != len(set(values)):
            errors.append(f"{relative}: metadata field {field_name!r} contains duplicate values")

        terms = dimension["terms"]
        for term_id in values:
            term = terms.get(term_id)
            if term is None:
                errors.append(f"{relative}: unknown {dimension_id} taxonomy term {term_id!r}")
                continue
            governance = term["governance"]
            if governance["status"] != "active":
                replacement = governance.get("replaced_by")
                suffix = f"; use {replacement!r}" if replacement else ""
                errors.append(
                    f"{relative}: deprecated {dimension_id} taxonomy term {term_id!r}{suffix}"
                )

        selected[dimension_id] = values

    expected_tags: set[str] = set()
    for dimension_id, dimension in dimensions.items():
        if dimension.get("docusaurus_tags"):
            expected_tags.update(selected.get(dimension_id, []))

    raw_tags = front_matter.get("tags", [])
    if isinstance(raw_tags, str):
        actual_tags = [raw_tags]
    elif isinstance(raw_tags, list) and all(isinstance(item, str) for item in raw_tags):
        actual_tags = list(raw_tags)
    else:
        errors.append(f"{relative}: tags must be a string list")
        actual_tags = []

    if len(actual_tags) != len(set(actual_tags)):
        errors.append(f"{relative}: tags contains duplicate values")

    if set(actual_tags) != expected_tags:
        errors.append(
            f"{relative}: tags is out of sync with governed Docusaurus-tag dimensions; expected "
            f"{sorted(expected_tags)!r}, found {sorted(set(actual_tags))!r}. "
            "Run `python scripts/taxonomy.py sync " + relative + "`."
        )

    return errors


def sync_document_tags(path: Path, taxonomy: dict[str, Any]) -> bool:
    front_matter, body = load_front_matter(path)
    desired: list[str] = []
    for dimension in taxonomy["dimensions"].values():
        if not dimension.get("docusaurus_tags"):
            continue
        field_name = dimension["metadata_field"]
        values = value_as_list(front_matter.get(field_name, [])) or []
        desired.extend(values)

    desired = sorted(set(desired))
    current = value_as_list(front_matter.get("tags", [])) or []
    if current == desired:
        return False

    if desired:
        front_matter["tags"] = desired
    elif "tags" in front_matter:
        del front_matter["tags"]
    write_front_matter(path, front_matter, body)
    return True


def all_docs(root: Path) -> list[Path]:
    docs_root = root / "docs"
    if not docs_root.exists():
        return []
    return sorted(
        path
        for path in docs_root.rglob("*")
        if path.is_file() and path.suffix.lower() in DOC_SUFFIXES
    )


def git_changed_paths(root: Path, base_sha: str) -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", f"{base_sha}...HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [root / line.strip() for line in result.stdout.splitlines() if line.strip()]


def expand_explicit_paths(root: Path, raw_paths: Iterable[str]) -> list[Path]:
    found: set[Path] = set()
    for raw in raw_paths:
        path = Path(raw)
        if not path.is_absolute():
            path = root / path
        if path.is_dir():
            found.update(
                child
                for child in path.rglob("*")
                if child.is_file() and child.suffix.lower() in DOC_SUFFIXES
            )
        elif path.is_file() and path.suffix.lower() in DOC_SUFFIXES:
            found.add(path)
    return sorted(found)


def select_docs(
    root: Path,
    *,
    explicit_paths: list[str],
    all_files: bool,
    changed_base: str | None,
) -> list[Path]:
    if all_files:
        return all_docs(root)
    if changed_base:
        changed = git_changed_paths(root, changed_base)
        taxonomy_changed = any(
            path.resolve() == (root / TAXONOMY_PATH).resolve() for path in changed
        )
        if taxonomy_changed:
            return all_docs(root)
        docs_root = (root / "docs").resolve()
        return sorted(
            path
            for path in changed
            if path.exists()
            and path.is_file()
            and path.suffix.lower() in DOC_SUFFIXES
            and docs_root in path.resolve().parents
        )
    return expand_explicit_paths(root, explicit_paths)


def suspicious_technology_terms(taxonomy: dict[str, Any]) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    technologies = taxonomy["dimensions"]["technologies"]
    for term_id, term in active_terms(technologies).items():
        description = term["description"]
        matches = [name for name, pattern in ORGANISATION_LIKE_DESCRIPTION_PATTERNS if pattern.search(description)]
        if matches:
            warnings.append(
                {
                    "id": term_id,
                    "label": term["label"],
                    "kind": term.get("kind", ""),
                    "signals": ", ".join(matches),
                    "description": description,
                }
            )
    return warnings


def command_generate(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    try:
        taxonomy = load_and_validate_taxonomy(root)
        generate_derived_files(root, taxonomy)
    except (ValidationError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


def command_check(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    errors: list[str] = []
    try:
        taxonomy = load_and_validate_taxonomy(root)
        errors.extend(check_derived_files(root, taxonomy))
    except (ValidationError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if not args.taxonomy_only:
        try:
            docs = select_docs(
                root,
                explicit_paths=args.paths,
                all_files=args.all,
                changed_base=args.changed_base,
            )
        except subprocess.CalledProcessError as error:
            print(f"ERROR: git diff failed: {error}", file=sys.stderr)
            return 1
        for path in docs:
            errors.extend(validate_document_front_matter(path, root, taxonomy))
        print(f"validated {len(docs)} documentation file(s)")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("taxonomy and metadata validation passed")
    return 0


def command_sync(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    try:
        taxonomy = load_and_validate_taxonomy(root)
        docs = select_docs(
            root,
            explicit_paths=args.paths,
            all_files=args.all,
            changed_base=args.changed_base,
        )
    except (ValidationError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    changed = 0
    for path in docs:
        try:
            if sync_document_tags(path, taxonomy):
                changed += 1
                print(f"synced {path.relative_to(root).as_posix()}")
        except ValidationError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 1

    generate_derived_files(root, taxonomy)
    print(f"updated tags in {changed} documentation file(s)")
    return 0


def command_audit_technologies(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    try:
        taxonomy = load_and_validate_taxonomy(root)
    except (ValidationError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    technologies = active_terms(taxonomy["dimensions"]["technologies"])
    by_kind: dict[str, list[str]] = {}
    for term_id, term in technologies.items():
        by_kind.setdefault(term["kind"], []).append(term_id)

    print(f"active technologies: {len(technologies)}")
    for kind_id in sorted(by_kind):
        label = taxonomy["technology_kinds"][kind_id]["label"]
        print(f"  {kind_id} ({label}): {len(by_kind[kind_id])}")

    warnings = suspicious_technology_terms(taxonomy)
    if warnings:
        print("\nPotential organisation/entity misclassifications:")
        for warning in warnings:
            print(
                f"WARNING: technologies.{warning['id']} [{warning['kind']}]: "
                f"{warning['description']} (signals: {warning['signals']})"
            )
    else:
        print("\nNo organisation-like technology descriptions detected.")

    return 1 if args.strict and warnings else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Repository taxonomy tooling")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("generate", help="Generate Docusaurus/VS Code derived files")

    check = subparsers.add_parser("check", help="Validate taxonomy and front matter")
    check.add_argument("paths", nargs="*", help="Documentation files or directories")
    check.add_argument("--all", action="store_true", help="Validate every docs/**/*.md[x] file")
    check.add_argument(
        "--changed-base",
        help="Validate Markdown/MDX changed since this git SHA; taxonomy changes validate all docs",
    )
    check.add_argument(
        "--taxonomy-only",
        action="store_true",
        help="Validate taxonomy and generated files but skip document metadata",
    )

    sync = subparsers.add_parser("sync", help="Synchronise derived front-matter tags")
    sync.add_argument("paths", nargs="*", help="Documentation files or directories")
    sync.add_argument("--all", action="store_true", help="Synchronise every docs/**/*.md[x] file")
    sync.add_argument("--changed-base", help="Synchronise docs changed since this git SHA")

    audit = subparsers.add_parser(
        "audit-technologies",
        help="Summarise technology kinds and flag organisation-like descriptions",
    )
    audit.add_argument(
        "--strict",
        action="store_true",
        help="Return exit code 1 if organisation-like terms are detected",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command in {"check", "sync"}:
        modes = int(bool(args.all)) + int(bool(args.changed_base)) + int(bool(args.paths))
        if getattr(args, "taxonomy_only", False):
            if modes:
                parser.error("--taxonomy-only cannot be combined with document selection")
        elif modes > 1:
            parser.error("choose one of explicit paths, --all, or --changed-base")

    if args.command == "generate":
        return command_generate(args)
    if args.command == "check":
        return command_check(args)
    if args.command == "sync":
        return command_sync(args)
    if args.command == "audit-technologies":
        return command_audit_technologies(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
