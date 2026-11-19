"""Plan check execution and share one source snapshot across scopes."""
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from qa_checks.base import BaseCheck, CheckResult, FileCheck, execute_check


@dataclass
class CheckPlan:
    page: list[BaseCheck]
    site: list[BaseCheck]
    files: list[FileCheck]
    checks: list[BaseCheck]

    @classmethod
    def for_mode(cls, mode: str, checks: Sequence[BaseCheck]) -> "CheckPlan":
        page, site, files, scoped = [], [], [], []
        for check in checks:
            if isinstance(check, FileCheck):
                files.append(check)
                continue
            run_page = mode in {"per-page", "all"} and check.supports_page
            run_site = mode in {"site-wide", "all"} and check.supports_site
            if run_page:
                page.append(check)
            if run_site:
                site.append(check)
            if run_page or run_site:
                scoped.append(check)
        return cls(page, site, files, [*scoped, *files])


def run_checks(paths: Sequence[Path], plan: CheckPlan, api_key: str | None, *, cached_check) -> CheckResult:
    result = CheckResult()
    if plan.page or plan.site:
        contents = {path.as_posix(): path.read_text(encoding="utf-8") for path in paths}

        if plan.page:
            for file_number, path in enumerate(paths, start=1):
                location = path.as_posix()
                content = contents[location]
                if not content.strip():
                    continue
                print(f"[{file_number}/{len(paths)}] {location}")
                for check in plan.page:
                    print(f"    {check.name}")
                    result.extend(execute_check(check, location, lambda: cached_check(
                        check, {location: content}, "per-page",
                        lambda: check.run_page(path, content, api_key))))

        for check in plan.site:
            print(f"[site] {check.name}")
            result.extend(execute_check(check, "<site-wide>", lambda: cached_check(
                check, contents, "site-wide", lambda: check.run_site(paths, contents, api_key))))

    for check in plan.files:
        print(f"[{check.source}] {check.name}")
        result.extend(check.run(paths))
    return result
