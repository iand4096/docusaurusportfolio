"""Response contracts and examples for the generated OpenAPI reference."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.retrieval import RetrievalMode


class SearchResult(BaseModel):
    id: str = Field(description='Stable ID of the indexed passage.')
    source: str = Field(description='Repository-relative path of the source document.')
    title: str
    heading: str
    heading_id: str | None = None
    url: str = Field(description='Link to the source passage, including its section anchor when available.')
    text: str
    facets: dict[str, list[str]]
    score: float = Field(description='Reciprocal rank fusion score used to order results.')


class RetrievalResponse(BaseModel):
    mode: RetrievalMode = Field(description='Retrieval mode actually used.')
    index_version: str = Field(description='First 12 characters of the indexed source hash.')


class SearchResponse(RetrievalResponse):
    results: list[SearchResult]


SEARCH_REQUEST_EXAMPLES = {
    'taxonomy-filter': {
        'summary': 'Search with a taxonomy filter',
        'value': {
            'query': 'How is documentation taxonomy governed?',
            'filters': {'topics': ['taxonomy']},
            'top_k': 1,
            'mode': 'bm25',
        },
    },
}

SEARCH_RESPONSE_EXAMPLES = {
    'taxonomy-filter': {
        'summary': 'One ranked passage with a source link',
        'value': {
            'results': [{
                'id': '3b036ef113b501655f03aada',
                'source': 'docs/case-studies/RagSearchCloudArchitecture.md',
                'title': 'Designing Cloud-Based RAG search for technical documentation',
                'heading': 'Project context',
                'heading_id': 'project-overview',
                'url': (
                    'https://iand4096.github.io/docusaurusportfolio/docs/case-studies/'
                    'RagSearchCloudArchitecture#project-overview'
                ),
                'text': 'I saw an opportunity to use document metadata, such as whether an API was current '
                        'or deprecated, to control which content was retrieved.',
                'facets': {'topics': ['taxonomy']},
                'score': 0.016393,
            }],
            'mode': 'bm25',
            'index_version': 'a1b2c3d4e5f6',
        },
    },
}


class Citation(BaseModel):
    id: int = Field(description='Number used to reference this source in the answer.')
    title: str
    url: str
    heading: str


class ChatResponse(RetrievalResponse):
    answer: str = Field(description='Answer grounded in the retrieved passages, with numbered source citations.')
    sources: list[Citation]


class TaxonomyDimension(BaseModel):
    label: str
    terms: dict[str, str] = Field(description='Active canonical term IDs mapped to their display labels.')


class TaxonomyResponse(BaseModel):
    version: int
    dimensions: dict[str, TaxonomyDimension]


class IndexManifest(BaseModel):
    model_config = ConfigDict(extra='allow')

    source_hash: str
    taxonomy_version: int
    chunks: int
    embedding_model: str | None
    semantic_enabled: bool


class HealthResponse(BaseModel):
    status: Literal['ok']
    index_loaded: bool
    index: IndexManifest | None


class ErrorResponse(BaseModel):
    detail: str


class InvalidSearchResponse(BaseModel):
    detail: list[dict] | dict = Field(description='Request validation issues or a canonical taxonomy filter error.')


RETRY_AFTER = {'Retry-After': {
    'description': 'Seconds to wait before retrying when the request is throttled.',
    'schema': {'type': 'integer'},
}}

RETRIEVAL_ERRORS = {
    409: {'model': ErrorResponse, 'description': 'Semantic retrieval is unavailable in the current index.'},
    422: {'model': InvalidSearchResponse, 'description': 'Invalid request body or taxonomy filters.'},
    429: {'model': ErrorResponse, 'description': 'Rate limit exceeded.', 'headers': RETRY_AFTER},
}
