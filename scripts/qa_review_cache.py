"""Disposable cache of completed AI checks, before feedback is attached."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile

SCHEMA = 1


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


class ReviewCache:
    def __init__(self, directory, *, enabled=True):
        self.directory = Path(directory)
        self.enabled = enabled

    def run(self, inputs, compute):
        if not self.enabled:
            return compute()
        key = digest({'schema': SCHEMA, 'inputs': inputs})
        path = self.directory / (key + '.json')
        try:
            entry = json.loads(path.read_text(encoding='utf-8'))
            findings = entry['findings']
            if (entry['schema'] == SCHEMA and entry['key'] == key
                    and isinstance(findings, list)
                    and all(isinstance(issue, dict) and issue.get('source') == 'ai'
                            and all(field in issue for field in ('file', 'line', 'original',
                                    'message', 'suggestion', 'severity', 'confidence', 'type', 'category'))
                            for issue in findings)
                    and entry['digest'] == digest(findings)):
                print('    AI review cache: hit')
                return copy.deepcopy(findings)
        except (OSError, ValueError, KeyError, TypeError):
            pass
        print('    AI review cache: miss')
        # Exceptions are never cached. Empty successful results are cacheable.
        findings = compute()
        entry = {'schema': SCHEMA, 'key': key, 'findings': findings, 'digest': digest(findings)}
        temporary = None
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.directory,
                                             suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(entry, stream, ensure_ascii=False)
            os.replace(temporary, path)
        except OSError as error:
            print(f'    AI review cache write unavailable: {error}')
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
        return findings
