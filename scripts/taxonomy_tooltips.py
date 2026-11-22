"""Review semantic tooltip evidence. Only the audit command can load NLP models."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from jsonschema import Draft202012Validator, FormatChecker, ValidationError as SchemaError
import taxonomy

ROOT = Path(__file__).resolve().parents[1]
POLICIES = Path("taxonomy/tooltip-policies.yml")
DECISIONS = Path("taxonomy/tooltip-decisions.json")
DEFINITIONS = Path("taxonomy/definition-reviews.yml")
OCCURRENCE = ("term_id", "term_fingerprint", "matched_text", "source_range", "context_hash")
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"


def read_artifact(root, path):
    file = root / path
    value = taxonomy.load_yaml(file) if file.suffix == ".yml" else json.loads(file.read_text())
    schema = (root / path).with_suffix(".schema.json")
    try:
        Draft202012Validator(json.loads(schema.read_text()), format_checker=FormatChecker()).validate(value)
    except SchemaError as error:
        raise taxonomy.ValidationError(f"{path}: {error.message}") from error
    return value


def technologies(data):
    return data["dimensions"]["technologies"]["terms"]


def term_basis(term):
    return [term.get("label"), term.get("description"), term.get("kind"),
            term.get("aliases", []), term["governance"]["status"]]


def digest(value):
    data = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return "sha256:" + hashlib.sha256(data.encode()).hexdigest()


def delta(before, after):
    old, new = technologies(before), technologies(after)
    return {key for key in old.keys() | new.keys()
            if key not in old or key not in new or term_basis(old[key]) != term_basis(new[key])}


def scan(root, candidate=None, overrides=None, strict=False, files=None):
    if strict:
        for artifact in (POLICIES, DECISIONS, DEFINITIONS):
            read_artifact(root, artifact)
    payload = {
        "root": str(root), "candidate": candidate, "overrides": overrides or {},
        "files": files if files is not None else [p.relative_to(root).as_posix() for p in taxonomy.all_docs(root)],
        "strict": strict,
    }
    result = subprocess.run(
        ["node", str(ROOT / "scripts/taxonomy-tooltip-scan.mjs")],
        input=json.dumps(payload), encoding="utf-8", capture_output=True, check=False,
    )
    if result.returncode:
        raise taxonomy.ValidationError(result.stderr.strip())
    return json.loads(result.stdout)


def evidence_context(excerpt):
    return digest(" ".join(excerpt.split()))


def definition_findings(report):
    """Find conflicting explicit expansions and flag the known RICE baseline."""
    findings = []
    for term_id, term in report["terms"].items():
        label = term["label"]
        if not re.fullmatch(r"[A-Z]{2,8}", label):
            continue
        pattern = re.compile(r"\b" + re.escape(label) + r"\s*\(\s*\**([A-Za-z][A-Za-z -]{3,90})\**\s*\)")
        records = {}
        for file, document in report["documents"].items():
            for occurrence in document["candidates"] + document.get("excluded_evidence", []):
                if occurrence["term_id"] != term_id:
                    continue
                context = occurrence["context"]
                for match in pattern.finditer(context):
                    expansion = match[1].strip()
                    words = expansion.split()
                    if len(words) < 2 or not all(word[0].isupper() for word in words):
                        continue
                    records.setdefault(expansion.casefold(), {
                        "path": file, "excerpt": context, "context_hash": evidence_context(context),
                    })
        if len(records) > 1 or (term_id == "rice" and records and
                               "regression testing and data ingestion" in term["description"]):
            findings.append({
                "id": f"{term_id}-definition-mismatch", "term_id": term_id,
                "taxonomy_definition_fingerprint": term["definition_hash"],
                "canonical_description": term["description"],
                "finding_type": "acronym_or_function_mismatch",
                "evidence": list(records.values()), "status": "needs_review",
            })
    return findings


def definition_errors(root, report, changed=(), overrides=None, preflight=False):
    errors = []
    records = read_artifact(root, DEFINITIONS)["findings"]
    for finding in definition_findings(report):
        if finding["id"] not in records:
            errors.append("Unrecorded definition finding " + finding["id"])
    for finding_id, entry in records.items():
        term = report["terms"].get(entry["term_id"])
        if not term or term["definition_hash"] != entry["taxonomy_definition_fingerprint"]:
            errors.append("Stale definition fingerprint: " + finding_id)
            continue
        for evidence in entry["evidence"]:
            file = (root / evidence["path"]).resolve()
            if not file.is_relative_to((root / "docs").resolve()) or not file.is_file():
                errors.append("Invalid definition evidence path: " + finding_id)
                continue
            source = (overrides or {}).get(evidence["path"], file.read_text())
            if (" ".join(evidence["excerpt"].split()) not in " ".join(source.split()) or
                    evidence_context(evidence["excerpt"]) != evidence["context_hash"]):
                errors.append("Stale definition evidence: " + finding_id)
        status = entry["status"]
        if status in {"needs_review", "confirmed_inconsistent"} and (
                entry["term_id"] in changed or entry["term_id"] in {
                    key for key, term_policy in report["policies"].items()
                    if term_policy["mode"] == "contextual" and term_policy["review"]["status"] == "approved"
                }):
            errors.append("Unresolved definition finding: " + finding_id)
        if status == "resolved_taxonomy":
            migration_path = (root / entry.get("resolution_migration", "")).resolve()
            if not migration_path.is_relative_to(root / "taxonomy/migrations") or not migration_path.is_file():
                errors.append("Missing definition correction migration: " + finding_id)
                continue
            migration = taxonomy.load_yaml(migration_path)
            taxonomy.validate_migration_schema(migration, root / taxonomy.MIGRATION_SCHEMA_PATH)
            updates = migration["changes"].get("technologies", {}).get("update", {})
            patch = updates.get(entry["term_id"], {})
            prior = patch.get("expect", {}).get("description")
            if (patch.get("set", {}).get("description") != term["description"] or
                    not isinstance(prior, str) or prior == term["description"] or
                    entry.get("previous_definition_fingerprint") != digest(prior)):
                errors.append("Definition correction is not evidenced by migration: " + finding_id)
            if not preflight:
                current = technologies(taxonomy.load_yaml(root / taxonomy.TAXONOMY_PATH))
                if current.get(entry["term_id"], {}).get("description") != term["description"]:
                    errors.append("Definition correction has not been applied: " + finding_id)
        if status == "resolved_documentation":
            triggering = entry.get("superseded_evidence", {})
            file = (root / triggering.get("path", "")).resolve()
            if (not file.is_relative_to(root / "docs") or not file.is_file() or not triggering.get("excerpt") or
                    " ".join(triggering["excerpt"].split()) in " ".join(
                        (overrides or {}).get(triggering["path"], file.read_text()).split())):
                errors.append("Documentation correction has not been verified: " + finding_id)
        if status == "distinct_concepts" and entry.get("related_term_id") not in report["terms"]:
            errors.append("Distinct concept needs a canonical mapping: " + finding_id)
    return errors


def check(root, before=None, candidate=None, overrides=None):
    current = candidate or taxonomy.load_yaml(root / taxonomy.TAXONOMY_PATH)
    changed = delta(before, current) if before else set()
    report = scan(root, candidate, overrides, strict=True)
    errors = report["errors"] + definition_errors(root, report, changed, overrides, preflight=candidate is not None)
    for term_id in sorted(changed):
        term = technologies(current).get(term_id)
        if term and term["governance"]["status"] == "active":
            approval = report["policies"].get(term_id)
            if (not approval or approval["review"]["status"] != "approved" or
                    approval["term_basis_hash"] != digest(term_basis(term))):
                errors.append("Changed technology needs a current tooltip policy: " + term_id)
    if errors:
        raise taxonomy.ValidationError("\n".join(errors))
    return report


def preflight(root, original, candidate, changed_docs):
    """Called before the first migration write for technology changes."""
    if (root / POLICIES).exists() and delta(original, candidate):
        overrides = {path.relative_to(root).as_posix(): taxonomy.render_front_matter(front, body)
                     for path, (front, body) in changed_docs.items()}
        check(root, original, candidate, overrides)


def migration_candidate(root, filename):
    file = (root / filename).resolve()
    if not file.is_relative_to(root / "taxonomy/migrations"):
        raise taxonomy.ValidationError("Expected a migration under taxonomy/migrations")
    migration = taxonomy.load_yaml(file)
    original = taxonomy.load_round_trip_yaml(root / taxonomy.TAXONOMY_PATH)
    taxonomy.validate_migration_schema(migration, root / taxonomy.MIGRATION_SCHEMA_PATH)
    taxonomy.validate_migration_semantics(original, migration, file)
    taxonomy.validate_migration_preconditions(original, migration)
    taxonomy.validate_contraction_references(root, original, migration)
    candidate, replacements, _ = taxonomy.build_migrated_taxonomy(original, migration)
    taxonomy.validate_taxonomy_schema(candidate, root / taxonomy.SCHEMA_PATH)
    taxonomy.validate_taxonomy_semantics(candidate)
    counts = taxonomy.migration_operation_counts(migration)
    overrides = {}
    if any(counts[k] for k in ("update", "deprecate", "replace", "configuration")):
        changed, _, errors = taxonomy.preflight_migration_documents(root, candidate, replacements)
        if errors:
            raise taxonomy.ValidationError("\n".join(errors))
        overrides = {path.relative_to(root).as_posix(): taxonomy.render_front_matter(front, body)
                     for path, (front, body) in changed.items()}
    return original, candidate, overrides


def mention_evidence(report, selected, spacy_model=None, embedding_dir=None, cache_dir=None):
    nlp = encoder = None
    model = {"classifier_version": "1", "embedding_revision": REVISION, "availability": []}
    if spacy_model:
        try:
            import spacy
            if spacy.__version__ != "3.8.11":
                raise ValueError("Expected spaCy 3.8.11")
            nlp = spacy.load(spacy_model, disable=["ner"])
            if nlp.meta["version"] != "3.8.0" or nlp.meta["name"] != "core_web_sm":
                nlp = None
                raise ValueError("Expected en_core_web_sm 3.8.0")
            model["spacy_pipeline"] = nlp.meta["version"]
        except (ImportError, OSError, ValueError) as error:
            model["availability"].append(str(error))
    else:
        model["availability"].append("spaCy model not configured")
    if embedding_dir:
        try:
            from sentence_transformers import SentenceTransformer, __version__ as encoder_version
            if encoder_version != "6.3.0":
                raise ValueError("Expected Sentence Transformers 6.3.0")
            location = Path(embedding_dir).resolve()
            if location.name != REVISION or not location.is_dir():
                raise ValueError("Expected a local MiniLM snapshot at the pinned revision")
            encoder = SentenceTransformer(str(location), local_files_only=True, trust_remote_code=False,
                                          device="cpu", model_kwargs={"use_safetensors": True})
        except (ImportError, OSError, ValueError) as error:
            model["availability"].append(str(error))
    else:
        model["availability"].append("MiniLM snapshot not configured")
    candidates = [
        mention for document in report["documents"].values() for mention in document["candidates"]
        if not selected or mention["term_id"] in selected
    ]
    contexts = list(dict.fromkeys(item["context"] for item in candidates))
    parsed = dict(zip(contexts, nlp.pipe(contexts, batch_size=32))) if nlp else {}
    pos_targets = {}
    for index, item in enumerate(candidates):
        allowed = report["policies"].get(item["term_id"], {}).get("allowed_pos")
        marked = item.get("marked_context") or ""
        if nlp and allowed and marked.count("[[") == marked.count("]]") == 1:
            before, _, target = marked.partition("[[")
            label, _, after = target.partition("]]")
            if label == item["matched_text"]:
                pos_targets[index] = (before + label + after, len(before), len(before) + len(label))
    tagged = dict(zip(pos_targets, nlp.pipe(
        (entry[0] for entry in pos_targets.values()), batch_size=32))) if pos_targets else {}
    unresolved = []
    for index, item in enumerate(candidates):
        term, context = item["term_id"], item["context"]
        positive = negative = False
        if term == "react" and context in parsed and context.count("React") == 1:
            tokens = [token for token in parsed[context] if token.text == "React"]
            positive = any(token.dep_ == "compound" and token.head.text == "components" for token in tokens)
            negative = any(token.pos_ == "VERB" and token.dep_ == "ROOT" for token in tokens)
        allowed = report["policies"].get(term, {}).get("allowed_pos")
        if allowed:
            token = None
            if index in tagged:
                _, start, end = pos_targets[index]
                token = next((word for word in tagged[index]
                              if word.idx == start and word.idx + len(word.text) == end), None)
            observed = token.pos_ if token and token.pos_ not in {"", "X"} else None
            result = "unknown" if observed is None else "allowed" if observed in allowed else "mismatch"
            item["pos_evidence"] = {"allowed": allowed, "observed": observed, "result": result}
            if result == "mismatch":
                item["proposed_sense"] = "uncertain" if positive else "other_sense"
                item["rule"] = "pos-policy-conflict" if positive else "pos-policy-mismatch"
                continue
        hit = "technical-cue" if positive and not negative else "other-sense-cue" if negative and not positive else None
        item["proposed_sense"] = {"technical-cue": "technical_sense", "other-sense-cue": "other_sense"}.get(hit, "uncertain")
        item["rule"] = hit
        if not hit:
            unresolved.append(item)
    if encoder and unresolved:
        examples = {}
        for item in unresolved:
            policy = report["policies"].get(item["term_id"], {})
            positive, negative = policy.get("positive_examples", []), policy.get("negative_examples", [])
            if positive and negative:
                examples[item["term_id"]] = (positive, negative)
        comparable = [item for item in unresolved if item["term_id"] in examples]
        def embedding_context(item):
            return item["marked_context"] or item["context"]
        inputs = list(dict.fromkeys([embedding_context(item) for item in comparable] + [
            example for groups in examples.values() for group in groups for example in group
        ]))
        if inputs:
            import numpy as np
            cache_key = digest([model, report["taxonomy_hash"], report["policy_hash"], inputs]).split(":")[1]
            cache_file = cache_dir / (cache_key + ".npz") if cache_dir else None
            features = None
            if cache_file and cache_file.is_file():
                with np.load(cache_file, allow_pickle=False) as cached:
                    matrix = cached["embeddings"]
                    if matrix.shape == (len(inputs), 384) and np.isfinite(matrix).all():
                        features = matrix
            if features is None:
                features = encoder.encode(inputs, batch_size=32, normalize_embeddings=True)
                if cache_file:
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    np.savez_compressed(cache_file, embeddings=features)
            vectors = dict(zip(inputs, features))
        else:
            vectors = {}
        for item in comparable:
            vector = vectors[embedding_context(item)]
            positive, negative = [max(((float(vector @ vectors[example]), example) for example in group))
                                  for group in examples[item["term_id"]]]
            item["embedding_evidence"] = {"positive": positive, "negative": negative,
                                          "margin": positive[0] - negative[0]}
    return model


def review(root, report, approvals, before=None, candidate=None, overrides=None):
    manifest_path = root / DECISIONS
    manifest = read_artifact(root, DECISIONS)
    for file, decisions in approvals.items():
        source = report["documents"][file]
        values = []
        for approval in decisions:
            if approval["result"] not in {"accept", "reject"}:
                raise taxonomy.ValidationError("Review decisions must explicitly accept or reject")
            match = next((candidate for candidate in source["candidates"]
                          if all(candidate[key] == approval[key] for key in OCCURRENCE)), None)
            if not match or not match["source_range"]:
                raise taxonomy.ValidationError("Approval does not identify an audited occurrence")
            values.append({**{key: approval[key] for key in OCCURRENCE}, "result": approval["result"],
                           "review": approval["review"]})
        entry = {"content_hash": source["content_hash"],
                 "decisions": sorted(values, key=lambda value: (value["source_range"]["start"], value["term_id"]))}
        if file in manifest["documents"] and manifest["documents"][file] != entry:
            print("Replacing prior approved decisions for " + file, file=sys.stderr)
        manifest["documents"][file] = entry
    manifest.update({key: report[key] for key in ("taxonomy_hash", "policy_hash", "matching_contract_version", "model")})
    schema = json.loads(manifest_path.with_suffix(".schema.json").read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(manifest)
    previous = manifest_path.read_text()
    try:
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        check(root, before, candidate, overrides)
    except Exception:
        manifest_path.write_text(previous)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("command", choices=("audit", "review", "check", "definitions"))
    parser.add_argument("action", nargs="?", choices=("audit", "check"))
    parser.add_argument("--migration", type=Path)
    parser.add_argument("--base")
    parser.add_argument("--changed-base", help="Restrict mention audit output to modified documents")
    parser.add_argument("--term", action="append", default=[])
    parser.add_argument("--report", type=Path)
    parser.add_argument("--approvals", type=Path)
    parser.add_argument("--spacy-model")
    parser.add_argument("--embedding-dir")
    args = parser.parse_args()
    root = args.root.resolve()
    before = candidate = overrides = None
    if args.migration:
        before, candidate, overrides = migration_candidate(root, args.migration)
    elif args.base:
        revision = subprocess.check_output(
            ["git", "rev-parse", "--verify", args.base + "^{commit}"], cwd=root, text=True
        ).strip()
        before = taxonomy.round_trip_yaml().load(subprocess.check_output(
            ["git", "show", revision + ":taxonomy/taxonomy.yml"], cwd=root, text=True))
    if args.command == "check":
        check(root, before, candidate, overrides)
        print("Tooltip approvals and definition evidence verified")
    elif args.command == "definitions" and args.action == "check":
        errors = definition_errors(root, scan(root, candidate, overrides), overrides=overrides)
        if errors:
            raise taxonomy.ValidationError("\n".join(errors))
        print("Definition evidence verified")
    elif args.command == "review":
        if not args.report or not args.approvals:
            parser.error("review requires --report and --approvals")
        report = json.loads(args.report.read_text())
        review(root, report, json.loads(args.approvals.read_text()), before, candidate, overrides)
    else:
        report = scan(root, candidate, overrides)
        terms = set(args.term) or (delta(before, candidate) if candidate else set())
        findings = [item for item in definition_findings(report) if not terms or item["term_id"] in terms]
        report["definition_findings"] = findings
        if args.changed_base:
            revision = subprocess.check_output(
                ["git", "rev-parse", "--verify", args.changed_base + "^{commit}"], cwd=root, text=True
            ).strip()
            files = {file.relative_to(root).as_posix() for file in taxonomy.git_changed_paths(root, revision)}
            report["documents"] = {file: doc for file, doc in report["documents"].items() if file in files}
        if args.command != "definitions":
            report["model"] = mention_evidence(
                report, terms, args.spacy_model, args.embedding_dir, root / ".cache/taxonomy-tooltips")
        if terms:
            for document in report["documents"].values():
                document["candidates"] = [item for item in document["candidates"] if item["term_id"] in terms]
        if args.command == "definitions":
            report = {"version": 1, "definition_findings": findings}
        result = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        if args.report:
            if args.report.suffix != ".json" or args.report.resolve() in {
                    (root / file).resolve() for file in (DECISIONS, POLICIES, DEFINITIONS)}:
                raise taxonomy.ValidationError("Audit reports require a separate .json output path")
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(result)
            sections = ["# Semantic tooltip audit", "", "## Mention linking", ""]
            for file, document in report.get("documents", {}).items():
                for item in document["candidates"]:
                    line = f"- {file}:{item['line']} · {item['label']} · {item.get('proposed_sense', 'unassessed')}"
                    if item["matched_text"] != item["label"]:
                        line += f" · matched {item['matched_text']}"
                    if pos := item.get("pos_evidence"):
                        line += f" · POS {pos['observed'] or 'unknown'} ({pos['result']})"
                    sections.append(line)
            sections.extend(["", "## Definition consistency", ""])
            sections.extend(f"- {item['id']} · {item['status']} · {item['canonical_description']}" for item in findings)
            args.report.with_suffix(".md").write_text("\n".join(sections) + "\n")
        else:
            print(result, end="")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        sys.exit(str(error))
