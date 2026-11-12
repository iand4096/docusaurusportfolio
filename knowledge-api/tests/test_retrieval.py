from app.retrieval import matches, search

ROWS=[{'id':'a','title':'API Documentation','heading':'','text':'OpenAPI schema and API governance',
       'url':'/docs/a','facets':{'type':['case-study'],'technologies':['openapi'],'lifecycle':['current']}},
      {'id':'b','title':'Old project','heading':'','text':'OpenAPI legacy',
       'url':'/docs/b','facets':{'type':['case-study'],'technologies':['openapi'],'lifecycle':['archived']}}]

def test_archived_hidden():
    results=search(ROWS,'OpenAPI',top_k=5)
    assert [r['id'] for r in results]==['a']

def test_explicit_archived():
    assert len(search(ROWS,'OpenAPI',include_archived=True))==2

def test_filter():
    assert not matches(ROWS[0],{'technologies':['python']},False)
    assert len(search(ROWS,'OpenAPI',{'technologies':['openapi']}))==1


def test_exclusions_win_over_inclusions_and_archive_opt_in():
    assert search(ROWS, 'OpenAPI', filters={'lifecycle': ['archived']},
                  include_archived=True, exclude_filters={'lifecycle': ['archived']}) == []
    assert [r['id'] for r in search(ROWS, 'OpenAPI', include_archived=True,
            exclude_filters={'lifecycle': ['archived']}, top_k=1)] == ['a']
    assert matches({'facets': {}}, {}, True, {'technologies': ['openapi']})
