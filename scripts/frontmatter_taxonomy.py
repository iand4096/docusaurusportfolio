#!/usr/bin/env python3

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


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

    taxonomy_ai = root / "scripts" / "taxonomy_ai.py"

    if not taxonomy_ai.exists():
        print(
            f"ERROR: taxonomy AI script not found: {taxonomy_ai}",
            file=sys.stderr,
        )
        return 2

    temp_parent = root / ".frontmatter"
    temp_parent.mkdir(parents=True, exist_ok=True)

    print(
        f"Suggesting title, description, and taxonomy for: {relative_document.as_posix()}",
        flush=True,
    )

    with tempfile.TemporaryDirectory(
        prefix="taxonomy-review-",
        dir=temp_parent,
    ) as temp_dir:
        temp_path = Path(temp_dir)

        markdown_report = temp_path / "taxonomy-suggestions.md"
        json_report = temp_path / "taxonomy-suggestions.json"

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

        if not markdown_report.exists():
            print(
                "ERROR: metadata AI did not produce a Markdown review report",
                file=sys.stderr,
            )
            return result.returncode or 1

        code_command = shutil.which("code") or shutil.which("code.cmd")

        if not code_command:
            print(
                f"ERROR: VS Code command-line tool 'code' was not found.\n"
                f"Temporary report: {markdown_report}",
                file=sys.stderr,
            )
            return result.returncode or 1

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

        # TemporaryDirectory removes both reports here,
        # after the VS Code tab is closed.

        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())