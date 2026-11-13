from pathlib import Path
import pytest
from app.ingest import documents, section_chunks, chunks_from_body

BASE = 'https://example.github.io/portfolio/'


def test_explicit_ids_fences_and_unannotated_headings():
    body = '''## Installation {/* #install-v2 */}
Run the installer.

```md
## Not actually a heading
```

## Overview
A section without an explicit anchor.

## Installation {/* #install-second */}
Do it again.
'''
    sections = section_chunks(body)
    assert [h for h, _, _ in sections] == ['Installation', 'Overview', 'Installation']
    assert [anchor for _, anchor, _ in sections] == ['install-v2', None, 'install-second']
    assert '## Not actually a heading' in sections[0][2]
    assert len(chunks_from_body(body)) == 3


def test_multiple_chunks_preserve_section_anchor():
    body = '## A section {/* #my-section */}\n' + ('word ' * 200)
    sections = section_chunks(body, max_chars=90)
    assert len(sections) > 1
    assert all(anchor == 'my-section' for _, anchor, _ in sections)


def test_documents_return_complete_urls(tmp_path: Path):
    docs = tmp_path / 'docs'
    docs.mkdir()
    (tmp_path / 'taxonomy').mkdir()
    (tmp_path / 'taxonomy/taxonomy.yml').write_text('dimensions: {}\n')
    (docs / 'example.mdx').write_text('''---
title: Example
slug: /sample-doc
---
## First {/* #first */}
Text one.

## Plain
Text two.
''', encoding='utf-8')
    rows = documents(tmp_path, BASE)
    assert len(rows) == 2
    assert rows[0]['heading_id'] == 'first'
    assert rows[0]['url'] == 'https://example.github.io/portfolio/docs/sample-doc#first'
    assert rows[1]['heading_id'] is None
    assert rows[1]['url'] == 'https://example.github.io/portfolio/docs/sample-doc'


def test_duplicate_explicit_heading_ids_rejected():
    with pytest.raises(ValueError, match='Duplicate explicit heading ID'):
        section_chunks('## One {/* #same */}\nA.\n## Two {/* #same */}\nB.')
