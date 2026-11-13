#!/usr/bin/env python3
"""Preview or apply an evidenced, preconditioned organisation metadata mapping."""
import argparse
import copy
import json
import io
from pathlib import Path

import taxonomy as tools


def plan(root, manifest, taxonomy):
    if manifest.get("version") != 1 or manifest.get("taxonomy_version") != taxonomy["version"]:
        raise tools.ValidationError("Metadata mapping version does not match the taxonomy")
    changes = {}
    seen = set()
    for entry in manifest["documents"]:
        path = (root / entry["file"]).resolve()
        if not path.is_relative_to((root / "docs").resolve()) or path in seen:
            raise tools.ValidationError("Mapping paths must be unique documents under docs/")
        seen.add(path)
        front, body = tools.load_front_matter(path)
        if "landing-page" in front.get("type", []):
            raise tools.ValidationError(f"{entry['file']}: landing pages are excluded")
        values = entry["organisations"]
        if not isinstance(values, list) or len(values) > 1:
            raise tools.ValidationError(f"{entry['file']}: at most one employer is allowed")
        if values and entry.get("scope") != "whole-page-single-employer":
            raise tools.ValidationError(f"{entry['file']}: whole-page single-employer review is required")
        if set(entry["evidence"]) != set(values):
            raise tools.ValidationError(f"{entry['file']}: each organisation needs body evidence")
        if any(not quote or quote not in body for quote in entry["evidence"].values()):
            raise tools.ValidationError(f"{entry['file']}: evidence no longer matches the body")
        candidate = copy.deepcopy(front)
        if values:
            candidate["organisations"] = values
        else:
            candidate.pop("organisations", None)
        tools.sync_front_matter_tags(candidate, taxonomy)
        errors = tools.validate_front_matter_data(candidate, entry["file"], taxonomy)
        if errors:
            raise tools.ValidationError("\n".join(errors))
        current = list(front.get("organisations", []))
        if current == values and (values or "organisations" not in front) and candidate.get("tags") == front.get("tags"):
            continue  # Safe to re-run after successful application.
        if current != entry["expect"]:
            raise tools.ValidationError(f"{entry['file']}: organisation precondition failed")
        source = path.read_text(encoding="utf-8")
        header_end = len(source.splitlines(keepends=True)[0])
        field = "organisations:\n" + "".join(f"  - {value}\n" for value in values)
        if values and "organisations" not in front and candidate.get("tags") == front.get("tags"):
            changes[path] = source[:header_end] + field + source[header_end:]
        else:
            stream = io.StringIO()
            tools.round_trip_yaml().dump(candidate, stream)
            changes[path] = "---\n" + stream.getvalue() + "---\n" + body
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    taxonomy = tools.load_and_validate_taxonomy(root)
    manifest = json.loads(args.manifest.read_text())
    changes = plan(root, manifest, taxonomy)
    for path in changes:
        values = next(e["organisations"] for e in manifest["documents"] if (root / e["file"]).resolve() == path)
        print(f"{path.relative_to(root)}: {', '.join(values) if values else '(remove organisation metadata)'}")
    print(f"Documents requiring changes: {len(changes)}")
    if args.apply:
        snapshots = tools.snapshot_paths(changes)
        try:
            for path, content in changes.items():
                path.write_text(content, encoding="utf-8")
        except Exception:
            tools.restore_snapshots(snapshots)
            raise
        print("Applied metadata only; article bodies and existing classifications preserved.")
    else:
        print("Preview passed; no files changed. Use --apply after reviewing the mapping.")


if __name__ == "__main__":
    main()
