"""Write the HTML, JSON and Markdown reports from a shared QA result."""
import json
from pathlib import Path
from typing import Mapping

from .html_report import generate_html_report
from .markdown import generate_markdown_report
from .model import Report, ReportPaths


def write_reports(report: Report, paths: ReportPaths, check_sources: Mapping[str, str]) -> None:
    generate_html_report(report, paths, check_sources)
    generate_json_report(report, paths.json)
    generate_markdown_report(report, paths)


def generate_json_report(report: Report, destination: Path) -> None:
    destination.write_text(
        json.dumps(report.payload(), indent=2, ensure_ascii=False), encoding="utf-8")
