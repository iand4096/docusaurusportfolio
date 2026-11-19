"""Source links and feedback commands embedded by the report renderers."""
import os
from pathlib import Path
import re
import shlex
import subprocess
from urllib.parse import quote

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PORTFOLIO_URL = "https://iand4096.github.io/docusaurusportfolio"
GITHUB_REPOSITORY_FALLBACK = "iand4096/docusaurusportfolio"


def _run_git(*args):
    """Return stripped Git command output, or None when Git metadata is unavailable."""

    try:
        result = subprocess.run(
            ["git", *args],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None

    value = result.stdout.strip()
    return value or None


def github_repository():
    """Return the GitHub owner/repository used for report source links."""

    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if repository:
        return repository
    remote = _run_git("remote", "get-url", "origin")
    if remote:
        match = re.search(
            r"(?:github\.com[/:])(?P<repository>[^/\s]+/[^/\s]+?)(?:\.git)?$",
            remote,
            re.IGNORECASE,
        )
        if match:
            return match.group("repository")

    return GITHUB_REPOSITORY_FALLBACK


def github_revision():
    """Return the editable GitHub branch used by report source links."""

    return "main"

def github_file_url(file_path, line=None):
    """Build a GitHub blob URL for a repository-relative file and optional line."""

    if not isinstance(file_path, str):
        return None

    normalised = file_path.strip().replace("\\", "/")
    while normalised.startswith("./"):
        normalised = normalised[2:]

    if not normalised or normalised.startswith("<"):
        return None

    repository = github_repository().strip("/")
    revision = github_revision()
    repository_url = quote(repository, safe="/")
    revision_url = quote(revision, safe="")
    file_url = quote(normalised, safe="/")
    # `?plain=1` keeps GitHub in source-file view, and the fragment must come
    # after the query string so line anchors work as expected, e.g.
    # `...?plain=1#L22`.
    url = f"https://github.com/{repository_url}/blob/{revision_url}/{file_url}?plain=1"

    if isinstance(line, int) and line > 0:
        url += f"#L{line}"

    return url

def recurrence_command(command, report_reference, **options):
    args = ['python3', 'scripts/ai_docs_review.py', command, '--report', str(report_reference)]
    for name, value in options.items():
        args.extend(['--' + name.replace('_', '-'), str(value)])
    return shlex.join(args)
