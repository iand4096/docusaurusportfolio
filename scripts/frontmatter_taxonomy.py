#!/usr/bin/env python3

from pathlib import Path
import subprocess
import sys


def taxonomy_review_paths(
    root: Path,
    document: Path,
    *,
    create_parent: bool = False,
) -> tuple[Path, Path]:
    """Return persistent review paths mirroring the document path under docs/."""
    docs_root = (root / "docs").resolve()
    document = document.resolve()

    try:
        relative_to_docs = document.relative_to(docs_root)
    except ValueError as error:
        raise ValueError(
            f"document must be inside the workspace docs directory: {document}"
        ) from error

    review_dir = (
        root
        / ".frontmatter"
        / "taxonomy-reviews"
        / relative_to_docs.parent
    )

    if create_parent:
        review_dir.mkdir(parents=True, exist_ok=True)

    stem = relative_to_docs.stem

    return (
        review_dir / f"{stem}.review.md",
        review_dir / f"{stem}.review.json",
    )


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
        _, json_report = taxonomy_review_paths(
            root,
            document,
            create_parent=True,
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

    print(
        f"Suggesting title, description, and taxonomy for: "
        f"{relative_document.as_posix()}",
        flush=True,
    )
    print(
        f"Review will be saved to: {json_report.relative_to(root).as_posix()}",
        flush=True,
    )

    command = [
        sys.executable,
        str(taxonomy_ai),
        "--root",
        str(root),
        "--json-only",
        "--json-output",
        str(json_report),
        str(relative_document),
    ]

    result = subprocess.run(
        command,
        cwd=root,
    )

    if result.returncode != 0:
        print(
            "ERROR: metadata AI classification failed",
            file=sys.stderr,
        )
        return result.returncode

    if not json_report.is_file():
        print(f"ERROR: metadata AI did not produce expected review artifact: {json_report}", file=sys.stderr)
        return 1

    print(
        f"Saved taxonomy review: "
        f"{json_report.relative_to(root).as_posix()}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
