#!/usr/bin/env python3

from pathlib import Path
import subprocess
import sys


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "ERROR: expected Front Matter workspace and content file arguments",
            file=sys.stderr,
        )
        return 2

    root = Path(sys.argv[1]).resolve()
    document = Path(sys.argv[2]).resolve()

    frontmatter_taxonomy = root / "scripts" / "frontmatter_taxonomy.py"

    if not frontmatter_taxonomy.exists():
        print(
            f"ERROR: Front Matter taxonomy wrapper not found: {frontmatter_taxonomy}",
            file=sys.stderr,
        )
        return 2

    result = subprocess.run(
        [
            sys.executable,
            str(frontmatter_taxonomy),
            str(root),
            str(document),
            "--apply",
        ],
        cwd=root,
        check=False,
    )

    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())