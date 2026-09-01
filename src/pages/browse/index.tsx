import React, {useMemo, useState} from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';

import styles from './styles.module.css';
import navigationIndex from '../../generated/taxonomy-navigation.json';

type DimensionId =
  | 'content_types'
  | 'audiences'
  | 'topics'
  | 'technologies'
  | 'lifecycle';

type DocumentMetadataField =
  | 'type'
  | 'audiences'
  | 'topics'
  | 'technologies'
  | 'lifecycle';

type TaxonomyTerm = {
  id: string;
  label: string;
  description?: string;
  parent?: string;
};

type TaxonomyDimension = {
  id: DimensionId;
  label: string;
  metadataField: DocumentMetadataField;
  terms: TaxonomyTerm[];
};

type NavigationDocument = {
  id: string;
  title: string;
  description?: string;
  path: string;
  source?: string;
  type: string[];
  audiences: string[];
  topics: string[];
  technologies: string[];
  lifecycle: string[];
};

type TaxonomyNavigationIndex = {
  generatedFrom?: string | string[];
  taxonomyVersion?: number;
  dimensions: Record<DimensionId, TaxonomyDimension>;
  documents: NavigationDocument[];
};

type SelectedFilters = Record<DimensionId, Set<string>>;

const data = navigationIndex as TaxonomyNavigationIndex;

const DIMENSION_ORDER: DimensionId[] = [
  'content_types',
  'topics',
  'technologies',
  'audiences',
  'lifecycle',
];

const DEFAULT_DIMENSION_LABELS: Record<DimensionId, string> = {
  content_types: 'Content type',
  audiences: 'Audience',
  topics: 'Topic',
  technologies: 'Technology',
  lifecycle: 'Lifecycle',
};

function emptyFilters(): SelectedFilters {
  return {
    content_types: new Set<string>(),
    audiences: new Set<string>(),
    topics: new Set<string>(),
    technologies: new Set<string>(),
    lifecycle: new Set<string>(),
  };
}

function valuesForDimension(
  document: NavigationDocument,
  dimension: TaxonomyDimension,
): string[] {
  return document[dimension.metadataField] ?? [];
}

function termLabelMap(
  dimensions: Record<DimensionId, TaxonomyDimension>,
): Map<string, string> {
  const labels = new Map<string, string>();

  Object.values(dimensions).forEach((dimension) => {
    dimension.terms.forEach((term) => {
      labels.set(`${dimension.id}:${term.id}`, term.label);
    });
  });

  return labels;
}

function documentMatchesSearch(
  document: NavigationDocument,
  query: string,
  labels: Map<string, string>,
): boolean {
  if (!query) {
    return true;
  }

  const taxonomyLabels = DIMENSION_ORDER.flatMap((dimensionId) => {
    const dimension = data.dimensions[dimensionId];
    if (!dimension) {
      return [];
    }

    return valuesForDimension(document, dimension).map(
      (termId) => labels.get(`${dimensionId}:${termId}`) ?? termId,
    );
  });

  const haystack = [
    document.title,
    document.description ?? '',
    ...taxonomyLabels,
  ]
    .join(' ')
    .toLocaleLowerCase();

  return haystack.includes(query.toLocaleLowerCase());
}

function documentMatchesFilters(
  document: NavigationDocument,
  selected: SelectedFilters,
): boolean {
  return DIMENSION_ORDER.every((dimensionId) => {
    const selectedTerms = selected[dimensionId];

    if (selectedTerms.size === 0) {
      return true;
    }

    const dimension = data.dimensions[dimensionId];
    if (!dimension) {
      return true;
    }

    const documentValues = new Set(valuesForDimension(document, dimension));

    // OR within a dimension:
    // selecting Python + Docusaurus matches a document containing either.
    // Different dimensions are combined with AND by the outer every().
    return [...selectedTerms].some((termId) => documentValues.has(termId));
  });
}

function countDocumentsForTerm(
  documents: NavigationDocument[],
  dimension: TaxonomyDimension,
  termId: string,
): number {
  return documents.reduce((count, document) => {
    return valuesForDimension(document, dimension).includes(termId)
      ? count + 1
      : count;
  }, 0);
}

export default function BrowsePage(): React.JSX.Element {
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<SelectedFilters>(() => emptyFilters());

  const labels = useMemo(() => termLabelMap(data.dimensions), []);

  const filteredDocuments = useMemo(() => {
    return data.documents
      .filter((document) => documentMatchesSearch(document, query.trim(), labels))
      .filter((document) => documentMatchesFilters(document, selected))
      .sort((left, right) => left.title.localeCompare(right.title));
  }, [query, selected, labels]);

  const activeFilterCount = useMemo(
    () =>
      DIMENSION_ORDER.reduce(
        (count, dimensionId) => count + selected[dimensionId].size,
        0,
      ),
    [selected],
  );

  function toggleFilter(dimensionId: DimensionId, termId: string): void {
    setSelected((current) => {
      const next: SelectedFilters = {
        ...current,
        [dimensionId]: new Set(current[dimensionId]),
      };

      if (next[dimensionId].has(termId)) {
        next[dimensionId].delete(termId);
      } else {
        next[dimensionId].add(termId);
      }

      return next;
    });
  }

  function clearFilters(): void {
    setSelected(emptyFilters());
    setQuery('');
  }

  return (
    <Layout
      title="Browse knowledge"
      description="Browse portfolio content using the governed taxonomy."
    >
      <main className={`container margin-vert--lg ${styles.page}`}>
        <header className={styles.header}>
          <p className={styles.eyebrow}>Governed taxonomy</p>
          <h1>Browse knowledge</h1>
          <p className={styles.intro}>
            Explore content by type, topic, technology, audience, and lifecycle.
            The navigation is generated from the same controlled vocabulary used
            to validate document metadata. See the{' '}
            <Link to="/docs/case-studies/TaxonomyGovernance">
              taxonomy governance case study.
            </Link>{' '}
          </p>
        </header>

        <div className={styles.browser}>
          <aside className={styles.filters} aria-label="Taxonomy filters">
            <div className={styles.filterHeader}>
              <h2>Filter</h2>
              {activeFilterCount > 0 || query ? (
                <button
                  type="button"
                  className={styles.clearButton}
                  onClick={clearFilters}
                >
                  Clear all
                </button>
              ) : null}
            </div>

            <div className={styles.searchGroup}>
              <label htmlFor="taxonomy-search" className={styles.filterLabel}>
                Search
              </label>
              <input
                id="taxonomy-search"
                type="search"
                className={styles.searchInput}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search titles, descriptions, taxonomy…"
              />
            </div>

            {DIMENSION_ORDER.map((dimensionId) => {
              const dimension = data.dimensions[dimensionId];

              if (!dimension || dimension.terms.length === 0) {
                return null;
              }

              return (
                <section className={styles.filterGroup} key={dimensionId}>
                  <h3 className={styles.filterLabel}>
                    {dimension.label || DEFAULT_DIMENSION_LABELS[dimensionId]}
                  </h3>

                  <div className={styles.filterOptions}>
                    {dimension.terms.map((term) => {
                      const isSelected = selected[dimensionId].has(term.id);
                      const count = countDocumentsForTerm(
                        data.documents,
                        dimension,
                        term.id,
                      );

                      return (
                        <button
                          key={term.id}
                          type="button"
                          className={`${styles.filterChip} ${
                            isSelected ? styles.filterChipSelected : ''
                          }`}
                          aria-pressed={isSelected}
                          onClick={() => toggleFilter(dimensionId, term.id)}
                          title={term.description}
                        >
                          <span>{term.label}</span>
                          <span className={styles.count}>{count}</span>
                        </button>
                      );
                    })}
                  </div>
                </section>
              );
            })}
          </aside>

          <section className={styles.results} aria-live="polite">
            <div className={styles.resultsHeader}>
              <div>
                <p className={styles.resultCount}>
                  {filteredDocuments.length}{' '}
                  {filteredDocuments.length === 1 ? 'result' : 'results'}
                </p>
                {activeFilterCount > 0 ? (
                  <p className={styles.filterSummary}>
                    {activeFilterCount}{' '}
                    {activeFilterCount === 1 ? 'filter' : 'filters'} selected
                  </p>
                ) : null}
              </div>
            </div>

            {filteredDocuments.length > 0 ? (
              <div className={styles.resultGrid}>
                {filteredDocuments.map((document) => (
                  <article className={styles.card} key={document.id}>
                    <h2 className={styles.cardTitle}>
                      <Link to={document.path}>{document.title}</Link>
                    </h2>

                    {document.description ? (
                      <p className={styles.description}>
                        {document.description}
                      </p>
                    ) : null}

                    <div
                      className={styles.metadata}
                      aria-label={`Taxonomy for ${document.title}`}
                    >
                      {DIMENSION_ORDER.flatMap((dimensionId) => {
                        const dimension = data.dimensions[dimensionId];

                        if (!dimension) {
                          return [];
                        }

                        return valuesForDimension(document, dimension).map(
                          (termId) => (
                            <span
                              className={styles.metadataTag}
                              key={`${dimensionId}:${termId}`}
                              title={
                                dimension.label ||
                                DEFAULT_DIMENSION_LABELS[dimensionId]
                              }
                            >
                              {labels.get(`${dimensionId}:${termId}`) ?? termId}
                            </span>
                          ),
                        );
                      })}
                    </div>

                    <Link className={styles.readLink} to={document.path}>
                      Open content →
                    </Link>
                  </article>
                ))}
              </div>
            ) : (
              <div className={styles.emptyState}>
                <h2>No matching content</h2>
                <p>
                  Try removing a filter or using a broader search term.
                </p>
                <button
                  type="button"
                  className="button button--secondary"
                  onClick={clearFilters}
                >
                  Clear filters
                </button>
              </div>
            )}
          </section>
        </div>
      </main>
    </Layout>
  );
}
