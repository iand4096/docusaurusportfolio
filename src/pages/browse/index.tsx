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
  kind?: string;
};

type TechnologyKind = {
  id: string;
  label: string;
  description?: string;
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
  technologyKinds?: Record<string, TechnologyKind>;
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


function initialFilters(): SelectedFilters {
  const filters = emptyFilters();

  if (typeof window === 'undefined') {
    return filters;
  }

  const params = new URLSearchParams(window.location.search);
  const validTypes = new Set(
    data.dimensions.content_types.terms.map((term) => term.id),
  );

  params.getAll('contentType').forEach((type) => {
    if (validTypes.has(type)) {
      filters.content_types.add(type);
    }
  });

  return filters;
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

// A dependency-free ranked search over the build-generated navigation metadata.
// It does not search full Markdown/MDX body text; that requires a richer build index.
function normalizeSearch(value: string): string {
  return value
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function editDistanceAtMostOne(left: string, right: string): boolean {
  if (Math.abs(left.length - right.length) > 1) return false;
  let i = 0;
  let j = 0;
  let edits = 0;
  while (i < left.length && j < right.length) {
    if (left[i] === right[j]) {
      i += 1;
      j += 1;
      continue;
    }
    if (++edits > 1) return false;
    if (left.length >= right.length) i += 1;
    if (right.length >= left.length) j += 1;
  }
  return edits + Number(i < left.length || j < right.length) <= 1;
}

function tokenStrength(token: string, normalizedText: string): number {
  if (!normalizedText) return 0;
  const words = normalizedText.split(' ');
  if (words.includes(token)) return 1;
  if (words.some(word => word.startsWith(token))) return 0.75;
  if (token.length >= 5 && words.some(word => word.length >= 5 && editDistanceAtMostOne(token, word))) {
    return 0.48;
  }
  return 0;
}

type RankedDocument = {document: NavigationDocument; score: number; matchedIn: string};

type SearchableDocument = {
  document: NavigationDocument;
  title: string;
  description: string;
  taxonomy: string;
  path: string;
};

function rankDocument(entry: SearchableDocument, query: string): RankedDocument | null {
  const normalized = normalizeSearch(query);
  if (!normalized) return {document: entry.document, score: 0, matchedIn: ''};
  const terms = [...new Set(normalized.split(' ').filter(Boolean))];
  let score = 0;
  let bestField = 'Taxonomy';
  let bestContribution = 0;

  for (const term of terms) {
    const fields = [
      {text: entry.title, weight: 10, label: 'Title'},
      {text: entry.description, weight: 4, label: 'Description'},
      {text: entry.taxonomy, weight: 3, label: 'Taxonomy'},
      {text: entry.path, weight: 1, label: 'Path'},
    ];
    const matching = fields.map(field => ({
      ...field,
      strength: tokenStrength(term, field.text),
    }));
    matching.sort((a, b) => b.strength * b.weight - a.strength * a.weight);
    const best = matching[0];
    if (!best || best.strength === 0) return null; // Require every query term.
    const contribution = best.strength * best.weight;
    score += contribution;
    if (contribution > bestContribution) {
      bestContribution = contribution;
      bestField = best.label;
    }
  }

  // Prefer phrase matches while still allowing words spread across fields.
  if (entry.title.includes(normalized)) score += 18;
  else if (entry.description.includes(normalized)) score += 7;
  else if (entry.taxonomy.includes(normalized)) score += 5;

  return {document: entry.document, score, matchedIn: bestField};
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


type TechnologyGroup = {
  id: string;
  label: string;
  description?: string;
  terms: TaxonomyTerm[];
};

function technologyGroups(dimension: TaxonomyDimension): TechnologyGroup[] {
  const groups = new Map<string, TechnologyGroup>();
  const kinds = data.technologyKinds ?? {};

  dimension.terms.forEach((term) => {
    const kindId = term.kind ?? 'other';
    const kind = kinds[kindId];

    if (!groups.has(kindId)) {
      groups.set(kindId, {
        id: kindId,
        label: kind?.label ?? (kindId === 'other' ? 'Other' : kindId),
        description: kind?.description,
        terms: [],
      });
    }

    groups.get(kindId)?.terms.push(term);
  });

  return [...groups.values()]
    .map((group) => ({
      ...group,
      terms: [...group.terms].sort((left, right) =>
        left.label.localeCompare(right.label),
      ),
    }))
    .sort((left, right) => left.label.localeCompare(right.label));
}

function DocumentTags({
  document,
  labels,
}: {
  document: NavigationDocument;
  labels: Map<string, string>;
}): React.JSX.Element {
  const [expanded, setExpanded] = useState(false);
  const tags = DIMENSION_ORDER.flatMap((dimensionId) => {
    const dimension = data.dimensions[dimensionId];
    return dimension
      ? valuesForDimension(document, dimension).map((termId) => ({dimensionId, termId}))
      : [];
  });
  const visibleTags = expanded ? tags : tags.slice(0, 5);

  return (
    <div className={styles.metadata} aria-label={`Taxonomy for ${document.title}`}>
      {visibleTags.map(({dimensionId, termId}) => (
        <span
          className={styles.metadataTag}
          key={`${dimensionId}:${termId}`}
          title={data.dimensions[dimensionId].label || DEFAULT_DIMENSION_LABELS[dimensionId]}
        >
          {labels.get(`${dimensionId}:${termId}`) ?? termId}
        </span>
      ))}
      {tags.length > 5 ? (
        <button
          type="button"
          className={styles.moreTags}
          aria-expanded={expanded}
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? 'Show fewer' : `+${tags.length - 5} more`}
        </button>
      ) : null}
    </div>
  );
}

export default function BrowsePage(): React.JSX.Element {
  const [query, setQuery] = useState('');
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  const [selected, setSelected] = useState<SelectedFilters>(initialFilters);

  const labels = useMemo(() => termLabelMap(data.dimensions), []);

  // Precompute normalized text once; only ranking and faceting change as users type.
  const searchableDocuments = useMemo<SearchableDocument[]>(() => data.documents.map(document => {
    const taxonomyLabels = DIMENSION_ORDER.flatMap(dimensionId => {
      const dimension = data.dimensions[dimensionId];
      return dimension
        ? valuesForDimension(document, dimension).map(termId =>
            labels.get(`${dimensionId}:${termId}`) ?? termId)
        : [];
    });
    return {
      document,
      title: normalizeSearch(document.title),
      description: normalizeSearch(document.description ?? ''),
      taxonomy: normalizeSearch(taxonomyLabels.join(' ')),
      path: normalizeSearch(document.path),
    };
  }), [labels]);

  const filteredDocuments = useMemo(() => {
    const searching = Boolean(normalizeSearch(query));
    const ranked = searchableDocuments
      .filter(entry => documentMatchesFilters(entry.document, selected))
      .map(entry => rankDocument(entry, query))
      .filter((match): match is RankedDocument => match !== null);
    ranked.sort((left, right) => searching
      ? right.score - left.score || left.document.title.localeCompare(right.document.title)
      : left.document.title.localeCompare(right.document.title));
    return ranked;
  }, [query, selected, searchableDocuments]);

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
                placeholder="Try OpenAPI, sample, or Docusaurus…"
                autoComplete="off"
              />
              <p className={styles.searchHelp}>Ranked search of titles, summaries and taxonomy.</p>
            </div>

            <button
              type="button"
              className={styles.mobileFiltersToggle}
              aria-controls="browse-taxonomy-filters"
              aria-expanded={mobileFiltersOpen}
              onClick={() => setMobileFiltersOpen((open) => !open)}
            >
              {mobileFiltersOpen ? 'Hide advanced filters' : 'Show advanced filters'}
              {activeFilterCount > 0 ? ` (${activeFilterCount} selected)` : ''}
            </button>
            <div
              id="browse-taxonomy-filters"
              className={`${styles.filterGroups} ${mobileFiltersOpen ? styles.filterGroupsOpen : ''}`}
            >
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

                  {dimensionId === 'technologies' && data.technologyKinds ? (
                    <div className={styles.filterOptions}>
                      {technologyGroups(dimension).map((group) => {
                        const hasSelectedTerm = group.terms.some((term) =>
                          selected.technologies.has(term.id),
                        );

                        return (
                          <details
                            key={group.id}
                            defaultOpen={hasSelectedTerm}
                            title={group.description}
                            style={{
                              width: '100%',
                              flexBasis: '100%',
                              marginTop: '0.35rem',
                            }}
                          >
                            <summary
                              style={{
                                cursor: 'pointer',
                                fontWeight: 600,
                              }}
                            >
                              {group.label} ({group.terms.length})
                            </summary>

                            <div className={styles.filterOptions}>
                              {group.terms.map((term) => {
                                const isSelected = selected.technologies.has(
                                  term.id,
                                );
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
                                      isSelected
                                        ? styles.filterChipSelected
                                        : ''
                                    }`}
                                    aria-pressed={isSelected}
                                    onClick={() =>
                                      toggleFilter('technologies', term.id)
                                    }
                                    title={term.description}
                                  >
                                    <span>{term.label}</span>
                                    <span className={styles.count}>
                                      {count}
                                    </span>
                                  </button>
                                );
                              })}
                            </div>
                          </details>
                        );
                      })}
                    </div>
                  ) : (
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
                  )}
                </section>
              );
            })}
            </div>
          </aside>

          <section className={styles.results} aria-live="polite">
            <div className={styles.resultsHeader}>
              <div>
                <p className={styles.resultCount}>
                  {filteredDocuments.length}{' '}
                  {filteredDocuments.length === 1 ? 'result' : 'results'}
                </p>
                {query.trim() && <p className={styles.rankingNote}>Sorted by relevance · All search terms must match</p>}
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
                {filteredDocuments.map(({document, matchedIn}) => (
                  <article className={styles.card} key={document.id}>
                    {query.trim() && <span className={styles.matchBadge}>Matched in {matchedIn.toLowerCase()}</span>}
                    <h2 className={styles.cardTitle}>
                      <Link to={document.path}>{document.title}</Link>
                    </h2>

                    {document.description ? (
                      <p className={styles.description}>
                        {document.description}
                      </p>
                    ) : null}

                    <DocumentTags document={document} labels={labels} />
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
                  Try fewer search words, check the spelling, or remove a taxonomy filter.
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
