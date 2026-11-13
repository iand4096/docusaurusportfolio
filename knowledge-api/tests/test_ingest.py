from pathlib import Path
from app.ingest import split_frontmatter, chunks_from_body, doc_url, strip_mdx

def test_ingestion_indexes_new_taxonomy_dimensions_and_metadata_fields(tmp_path):
    from app.ingest import documents
    from app.governance_filters import taxonomy_dimensions, validate_filters
    from app.retrieval import matches
    import yaml

    dimensions = {
        'organisations': {'metadata_field': 'organisations', 'terms': {
            'amx': {'label': 'AMX', 'governance': {'status': 'active'}}}},
        'projects': {'metadata_field': 'project_ids', 'terms': {
            'portal': {'label': 'Portal', 'governance': {'status': 'active'}}}},
    }
    tax = {'version': 3, 'dimensions': dimensions}
    (tmp_path / 'taxonomy').mkdir()
    (tmp_path / 'taxonomy/taxonomy.yml').write_text(yaml.safe_dump(tax))
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs/example.md').write_text(
        '---\ntitle: Example\norganisations: [amx]\nproject_ids: [portal]\n---\nAn example passage.')
    (tmp_path / 'docs/unassigned.md').write_text('---\ntitle: Other\n---\nAnother passage.')
    rows = documents(tmp_path, 'https://example.com/')
    selected = validate_filters({'organisations': ['amx'], 'project_ids': ['portal']}, taxonomy_dimensions(tax))
    matching = [row for row in rows if matches(row, selected, False)]
    assert len(matching) == 1
    assert matching[0]['facets'] == {'organisations': ['amx'], 'project_ids': ['portal']}
    assert all('projects' not in row['facets'] for row in rows)

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
