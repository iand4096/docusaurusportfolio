"""Verify proposed findings against source before reporting or caching them."""
import json

from . import client
from .prompts import COMMON_AI_RULES, DEFECT_VERIFICATION_CONTRACT, SUBSTANTIVE_DEFECT_RULES

def verify_page_findings(issues, path, content, api_key, defects_only=False):
    if defects_only:
        issues = [issue for issue in issues if issue.get('type') == 'defect']
    if not issues:
        return []
    response = client.request_review(
        COMMON_AI_RULES + """\nAudit proposed findings independently against the source.
Reject unsupported grammar diagnoses, self-contradictory explanations, unchanged
corrections, invented facts, stylistic preferences and useful repetition.
Check reader impact and all cited evidence. Return JSON {"assessments": [
{"index": 0, "supported": true, "reason": "specific evidence-based explanation", "medium_justified": false}]}.
Set medium_justified true only for demonstrated correctness or comprehension harm.
Assess every index exactly once. Do not rewrite findings or trust their confidence.
Preserve reasonable conventional readings. Reject speculative reader hesitation
and differences between display labels and API literals that cause no conflict.
""" + (SUBSTANTIVE_DEFECT_RULES + DEFECT_VERIFICATION_CONTRACT if defects_only else ''),
        json.dumps({'file': path.as_posix(), 'content': content, 'findings': issues}, ensure_ascii=False),
        api_key)
    assessments = response.get('assessments')
    if not isinstance(assessments, list):
        raise ValueError('Invalid finding verification response')
    by_index = {}
    for entry in assessments:
        if (not isinstance(entry, dict) or type(entry.get('index')) is not int
                or entry['index'] not in range(len(issues)) or entry['index'] in by_index
                or type(entry.get('supported')) is not bool
                or not isinstance(entry.get('reason'), str) or not entry['reason'].strip()):
            raise ValueError('Invalid finding verification assessment')
        by_index[entry['index']] = entry
    if len(by_index) != len(issues):
        raise ValueError('Incomplete finding verification')
    retained = []
    for i, issue in enumerate(issues):
        assessment = by_index[i]
        if not assessment['supported']:
            continue
        if defects_only:
            if type(assessment.get('substantive_defect')) is not bool:
                raise ValueError('Defect verification requires a substantive_defect boolean')
            if not assessment['substantive_defect']:
                continue
            fields = ('reasonable_reading', 'why_reading_fails', 'consequence')
            if any(not isinstance(assessment.get(field), str) or not assessment[field].strip() for field in fields):
                raise ValueError('Defect verification requires source-grounded reasoning')
            if assessment.get('failure_kind') not in {
                'wrong_instruction', 'contradiction', 'missing_prerequisite',
                'broken_reference', 'ambiguous_meaning', 'incorrect_language'}:
                raise ValueError('Invalid substantive failure kind')
            if assessment['failure_kind'] == 'ambiguous_meaning':
                interpretations = assessment.get('interpretations')
                if (not isinstance(interpretations, list) or len(interpretations) != 2
                        or any(not isinstance(text, str) or not text.strip() for text in interpretations)
                        or interpretations[0].strip() == interpretations[1].strip()):
                    raise ValueError('Ambiguity requires two distinct interpretations')
        issue = dict(issue, verification=assessment)
        if issue['severity'] == 'medium' and assessment.get('medium_justified') is not True:
            issue['severity'] = 'low'
        retained.append(issue)
    return retained
