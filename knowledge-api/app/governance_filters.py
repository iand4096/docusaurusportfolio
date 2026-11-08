"""Read-only validation of search facets against the canonical taxonomy.

This module does not alter the taxonomy or replace the existing repository
metadata governance checks, which remain an ingestion-time requirement.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException


def taxonomy_dimensions(tax: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Expose approved query fields and active canonical term IDs."""
    result: dict[str, dict[str, Any]] = {}
    for dimension_name, dimension in tax.get('dimensions', {}).items():
        field = dimension['metadata_field']
        terms = dimension.get('terms', {})
        result[field] = {
            'label': dimension_name,
            'terms': {
                term_id: entry.get('label', term_id)
                for term_id, entry in terms.items()
                if entry.get('governance', {}).get('status') == 'active'
            },
        }
    return result


def validate_filters(
    filters: dict[str, list[str]], dimensions: dict[str, dict[str, Any]]
) -> dict[str, list[str]]:
    """Reject unknown fields and non-active/non-canonical term identifiers.

    JSON/Pydantic handles type checks before this function is called. OR applies
    within a facet; AND applies across facet fields during retrieval.
    """
    for field, values in filters.items():
        if field not in dimensions:
            raise HTTPException(
                status_code=422,
                detail={'error': 'unknown_facet', 'facet': field,
                        'allowed_facets': sorted(dimensions)},
            )
        allowed = dimensions[field]['terms']
        if not values:
            raise HTTPException(status_code=422, detail={
                'error': 'empty_facet', 'facet': field,
                'message': 'Supply at least one canonical term ID.'
            })
        if any(not isinstance(value, str) or value not in allowed for value in values):
            invalid = [value for value in values if value not in allowed]
            raise HTTPException(status_code=422, detail={
                'error': 'unknown_or_inactive_term', 'facet': field,
                'invalid_values': invalid, 'allowed_values': sorted(allowed),
            })
    # Remove duplicates deterministically without modifying the input.
    return {field: list(dict.fromkeys(values)) for field, values in filters.items()}
