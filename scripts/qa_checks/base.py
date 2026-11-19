"""Shared check execution and structured outcomes."""
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypedDict


class CheckError(TypedDict):
    check: str
    file: str
    error: str


@dataclass
class CheckResult:
    issues: list[dict[str, Any]] = field(default_factory=list)
    errors: list[CheckError] = field(default_factory=list)

    def extend(self, result: "CheckResult") -> None:
        self.issues.extend(result.issues)
        self.errors.extend(result.errors)


class BaseCheck(ABC):
    name = "BaseCheck"
    supports_page = False
    supports_site = False
    source = "ai"
    defects_only = False

    def run_page(self, path, content, api_key):
        return []

    def run_site(self, paths, contents, api_key):
        return []


def execute_check(check: BaseCheck, location: str,
                  run: Callable[[], list[dict[str, Any]]]) -> CheckResult:
    try:
        return CheckResult(issues=run())
    except Exception as error:
        return CheckResult(errors=[{"check": check.name, "file": location, "error": str(error)}])


class FileCheck(BaseCheck):
    """An external tool with a preflight and one invocation across its inputs."""

    def __init__(self, root: Path = Path(".")):
        self.root = root

    @abstractmethod
    def preflight(self) -> str:
        """Validate configuration and resolve the executable."""

    @abstractmethod
    def run_files(self, paths: Sequence[Path], executable: str | None = None) -> list[dict[str, Any]]:
        """Execute the tool and normalise its findings."""

    def run(self, paths: Sequence[Path]) -> CheckResult:
        return execute_check(self, f"<{self.source}>",
                             lambda: self.run_files(paths, executable=self.preflight()))
