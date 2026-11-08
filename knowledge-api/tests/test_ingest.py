from pathlib import Path
from app.ingest import split_frontmatter, chunks_from_body, doc_url, strip_mdx

def test_frontmatter_lists():
    fm,body=split_frontmatter('---\ntype:\n  - case-study\n---\n# Hello')
    assert fm['type']==['case-study'] and body=='# Hello'

def test_mdx_and_heading_chunks():
    parsed=strip_mdx('import Widget from "x"\n# Intro\n<Widget />\nA paragraph.')
    assert 'import Widget' not in parsed and 'A paragraph.' in parsed
    assert chunks_from_body(parsed)[0][0]=='Intro'

def test_doc_url_slug():
    docs=Path('/repo/docs'); path=docs/'implementation-details'/'taxonomy.md'
    assert doc_url(path,docs,{},'https://example.com/portfolio/').endswith('/docs/implementation-details/taxonomy')
