#!/usr/bin/env python3

from pathlib import Path
import shutil
import subprocess
import sys


def taxonomy_review_paths(
    root: Path,
    document: Path,
    *,
    create_parent: bool = False,
) -> tuple[Path, Path]:
    """Return persistent review paths mirroring the document path under src/."""
    src_root = (root / "src").resolve()
    document = document.resolve()

    try:
        relative_to_src = document.relative_to(src_root)
    except ValueError as error:
        raise ValueError(
            f"document must be inside the workspace src directory: {document}"
        ) from error

    review_dir = (
        root
        / ".frontmatter"
        / "taxonomy-reviews"
        / relative_to_src.parent
    )

    if create_parent:
        review_dir.mkdir(parents=True, exist_ok=True)

    stem = relative_to_src.stem

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
        markdown_report, json_report = taxonomy_review_paths(
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
        f"Review artifacts will be saved under: "
        f"{markdown_report.parent.relative_to(root).as_posix()}",
        flush=True,
    )

    command = [
        sys.executable,
        str(taxonomy_ai),
        "--root",
        str(root),
        "--output",
        str(markdown_report),
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

    missing_reports = [
        path
        for path in (markdown_report, json_report)
        if not path.exists()
    ]
    if missing_reports:
        for path in missing_reports:
            print(
                f"ERROR: metadata AI did not produce expected review artifact: {path}",
                file=sys.stderr,
            )
        return 1

    code_command = shutil.which("code") or shutil.which("code.cmd")

    if not code_command:
        print(
            f"ERROR: VS Code command-line tool 'code' was not found.\n"
            f"Saved Markdown review: {markdown_report}\n"
            f"Saved JSON review: {json_report}",
            file=sys.stderr,
        )
        return 1

    print("Opening metadata suggestions in VS Code...", flush=True)

    subprocess.run(
        [
            code_command,
            "--reuse-window",
            "--wait",
            str(markdown_report),
        ],
        cwd=root,
    )

    print(
        f"Saved taxonomy review: "
        f"{markdown_report.relative_to(root).as_posix()}",
        flush=True,
    )
    print(
        f"Saved taxonomy review data: "
        f"{json_report.relative_to(root).as_posix()}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
