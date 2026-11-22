"""Adapt semantic tooltip evidence to report-only QA findings."""

from qa_checks.base import CheckResult, FileCheck
from qa_policy import make_issue
from taxonomy_tooltips import (
    DEFINITIONS, definition_errors, definition_findings, mention_evidence, read_artifact, scan,
)


class TooltipAuditCheck(FileCheck):
    name = "TooltipAuditCheck"
    source = "tooltip"

    def preflight(self):
        return "node"

    def issue(self, file, line, category, excerpt, message, suggestion, evidence=None):
        issue = make_issue(file=file, line=line, category=category, original=excerpt,
                           message=message, suggestion=suggestion, source=self.source,
                           severity="low", confidence="medium", issue_type="improvement")
        if evidence is not None:
            issue["tooltip_evidence"] = evidence
        return issue

    def run(self, paths):
        try:
            return CheckResult(issues=self.run_files(paths))
        except Exception as error:
            # The scanner can raise its own validation or model exceptions.
            return CheckResult(issues=[self.unavailable(error)])

    def unavailable(self, error):
        return self.issue("taxonomy/tooltip-policies.yml", 1, "tooltip-unavailable", "",
                          f"Tooltip audit evidence unavailable: {error}",
                          "Check the audit setup and rerun the tooltip check.")

    def run_files(self, paths, executable=None):
        root = self.root.resolve()
        docs = root / "docs"
        files = sorted({path.resolve().relative_to(root).as_posix()
                        for path in paths if path.resolve().is_relative_to(docs)})
        if not files:
            return []
        report = scan(root, files=files)
        issues = []
        try:
            model = mention_evidence(report, set(report["policies"]), spacy_model="en_core_web_sm")
        except Exception as error:
            issues.append(self.unavailable(error))
            model = mention_evidence(report, set(report["policies"]))
        issues.extend(self.unavailable(reason) for reason in model["availability"]
                      if reason not in {"MiniLM snapshot not configured", "spaCy model not configured"})
        for file, document in report["documents"].items():
            for mention in document["candidates"]:
                policy = report["policies"].get(mention["term_id"])
                if not policy or policy["mode"] != "contextual" or mention["current_decision"]:
                    continue
                message = f"{mention['label']} needs an occurrence review ({mention['proposed_sense']})."
                if pos := mention.get("pos_evidence"):
                    message += f" spaCy POS: {pos['observed'] or 'unknown'} ({pos['result']})."
                issues.append(self.issue(file, mention["line"], "tooltip-mention", mention["context"],
                                         message, "Review whether this occurrence refers to the canonical concept.",
                                         mention))
            for decision in document["stale_decisions"]:
                issues.append(self.issue(file, 1, "tooltip-stale-decision", decision["matched_text"],
                                         f"The saved decision for {decision['term_id']} no longer matches the source or policy.",
                                         "Audit the document again and refresh its approvals.", decision))
        records = read_artifact(root, DEFINITIONS)["findings"]
        findings = {item["id"]: item for item in definition_findings(report)}
        findings.update({key: item for key, item in records.items()
                         if item["status"] in {"needs_review", "confirmed_inconsistent"}})
        for error in definition_errors(root, report):
            finding_id = error.rsplit(" ", 1)[-1]
            if finding_id in records:
                findings[finding_id] = {**records[finding_id], "validation_note": error}
        for finding in findings.values():
            evidence = next((entry for entry in finding["evidence"] if entry["path"] in files), None)
            if evidence:
                match = next((item for item in report["documents"][evidence["path"]]["candidates"]
                              if item["context"] == evidence["excerpt"]), None)
                issues.append(self.issue(evidence["path"], match["line"] if match else 1, "tooltip-definition",
                                         evidence["excerpt"], finding.get("validation_note") or
                                         f"Review the canonical definition of {finding['term_id']}.",
                                         "Compare the source evidence with the canonical definition and record a disposition.",
                                         finding))
        return issues
