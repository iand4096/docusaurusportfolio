"""Evaluate retrieval on labelled historical complaints; never calls DeepSeek."""
import argparse
import json
from pathlib import Path

import qa_feedback as feedback
from qa_embeddings import ComplaintIndex, MODEL, REVISION
from qa_recurrence import candidates, previous_finding


def evaluate(fixture_path, feedback_path, *, index):
    fixture = json.loads(fixture_path.read_text())
    store = feedback.feedback_records(feedback_path)
    records = store['records']
    cases = fixture['cases']
    index.populate([case['finding'] for case in cases] + [previous_finding(r) for r in records.values()])
    rows = []
    for case in cases:
        issue = dict(case['finding'])
        issue['issue_id'] = feedback.finding_id(issue)
        ranking = candidates(issue, store, index=index)
        ids = [key for _, key, _ in ranking]
        old = previous_finding(records[case['previous']])
        rank = ids.index(case['previous']) + 1 if case['previous'] in ids else None
        rows.append({'name': case['name'], 'relationship': case['relationship'],
                     'expected_retrieval': case['retrieve'], 'candidate_rank': rank,
                     'complaint_cosine': index.similarity(issue, old),
                     'passed': rank is not None if case['retrieve'] else True})
    # Negative pairs can remain candidates through quotation overlap: the semantic
    # comparison, not retrieval, decides equivalence. Report their rank transparently.
    return {'model': MODEL, 'revision': REVISION, 'cases': rows,
            'passed': all(row['passed'] for row in rows),
            'scope': 'Retrieval smoke evaluation, not measured semantic/adjudication accuracy.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, default=Path('scripts/tests/fixtures/qa-recurrence-labelled.json'))
    parser.add_argument('--feedback-file', type=Path, default=feedback.DEFAULT_FEEDBACK)
    args = parser.parse_args()
    result = evaluate(args.fixtures, args.feedback_file, index=ComplaintIndex())
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
