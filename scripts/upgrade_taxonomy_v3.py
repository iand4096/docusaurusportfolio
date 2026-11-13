#!/usr/bin/env python3
"""Preview or apply the deterministic v2-to-v3 upgrade without rewriting documents."""
import argparse
import copy
from pathlib import Path

import taxonomy as tools


def upgrade(taxonomy):
    if taxonomy.get("version") != 2:
        raise tools.ValidationError("This upgrade requires taxonomy version 2")
    candidate = copy.deepcopy(taxonomy)
    candidate["version"] = 3
    candidate["dimensions"]["organisations"] = tools.organisation_dimension()
    tools.validate_taxonomy_semantics(candidate)
    return candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    path = args.root / tools.TAXONOMY_PATH
    candidate = upgrade(tools.load_yaml(path))
    tools.validate_taxonomy_schema(candidate, args.root / tools.SCHEMA_PATH)
    print("v2 → v3: add optional organisations dimension; existing dimensions and documents unchanged")
    if args.apply:
        tools.write_yaml(path, candidate)
        print("Applied schema upgrade. Add vocabulary, then regenerate derived files.")
    else:
        print("Preview passed; use --apply to write the canonical taxonomy.")


if __name__ == "__main__":
    main()
