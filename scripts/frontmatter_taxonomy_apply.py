#!/usr/bin/env python3

from pathlib import Path
import subprocess
import sys

from frontmatter_taxonomy import taxonomy_review_paths


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "ERROR: expected Front Matter workspace and content file arguments",
            file=sys.stderr,
        )
        return 2

    root = Path(sys.argv[1]).resolve()
    document = Path(sys.argv[2]).resolve()

    try:
        relative_document = document.relative_to(root)
    except ValueError:
        print(
            f"ERROR: document is outside workspace: {document}",
            file=sys.stderr,
        )
        return 2

    try:
        _markdown_report, json_report = taxonomy_review_paths(
            root,
            document,
            create_parent=False,
        )
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    taxonomy_ai = root / "scripts" / "taxonomy_ai.py"

    if not taxonomy_ai.exists():
        print(
            f"ERROR: taxonomy AI script not found: {taxonomy_ai}",
            file=sys.stderr,
        )
        return 2

    if not json_report.is_file():
        print(
            "ERROR: no saved taxonomy review exists for this document.\n"
            f"Document: {relative_document.as_posix()}\n"
            f"Expected review: {json_report.relative_to(root).as_posix()}\n"
            "Run 'Review metadata with DeepSeek' first.",
            file=sys.stderr,
        )
        return 2

    print(
        f"Applying reviewed taxonomy metadata for: "
        f"{relative_document.as_posix()}",
        flush=True,
    )
    print(
        f"Using review artifact: "
        f"{json_report.relative_to(root).as_posix()}",
        flush=True,
    )

    result = subprocess.run(
        [
            sys.executable,
            str(taxonomy_ai),
            "--root",
            str(root),
            "--apply-from",
            str(json_report),
        ],
        cwd=root,
        check=False,
    )

    if result.returncode != 0:
        print(
            "ERROR: reviewed taxonomy metadata was not applied",
            file=sys.stderr,
        )
        return result.returncode

    print(
        "Reviewed taxonomy metadata applied successfully. "
        "Review git diff before committing.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
