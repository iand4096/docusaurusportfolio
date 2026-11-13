import React, {useEffect, useState} from 'react';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import {Redirect} from '@docusaurus/router';
import useBaseUrl from '@docusaurus/useBaseUrl';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import styles from './styles.module.css';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type {Root, Nodes, PhrasingContent} from 'mdast';
import navigationIndex from '@site/src/generated/taxonomy-navigation.json';
import {ExploreTaxonomyFilterGroups} from '@site/src/components/ExploreTaxonomyFilterGroups';
import browseStyles from '@site/src/pages/browse/styles.module.css';

type RetrievalMode = 'bm25' | 'semantic' | 'hybrid';
type ResponseMode = 'search' | 'chat';
type FacetKey = 'type' | 'audiences' | 'topics' | 'technologies' | 'lifecycle';
type SelectedFacets = Partial<Record<FacetKey, string[]>>;
const FACETS: {key: FacetKey; label: string}[] = [
  {key: 'type', label: 'Content type'},
  {key: 'topics', label: 'Topic'},
  {key: 'technologies', label: 'Technology'},
  {key: 'audiences', label: 'Audience'},
  {key: 'lifecycle', label: 'Lifecycle'},
];

type TaxonomyDimension = {label: string; terms: Record<string, string>};
type TaxonomyResponse = {version: number; dimensions: Record<string, TaxonomyDimension>};
// Browse and AI Search use the same build-generated, active-only taxonomy.
// The search backend still validates submitted filter IDs against its own taxonomy.
type NavigationTaxonomy = {
  taxonomyVersion?: number;
  dimensions: Record<string, {
    label: string;
    metadataField: string;
    terms: {id: string; label: string}[];
  }>;
};
const navigationTaxonomy = navigationIndex as NavigationTaxonomy;
const LOCAL_TAXONOMY: TaxonomyResponse = {
  version: navigationTaxonomy.taxonomyVersion ?? 0,
  dimensions: Object.fromEntries(
    Object.values(navigationTaxonomy.dimensions).map(({label, metadataField, terms}) => [
      metadataField,
      {label, terms: Object.fromEntries(terms.map(({id, label}) => [id, label]))},
    ]),
  ),
};
type Evidence = {
  id?: string | number;
  title: string;
  heading?: string;
  url: string;
  text?: string;
  score?: number;
  facets?: Record<string, string[]>;
};
type ApiResponse = {
  answer?: string;
  results?: Evidence[];
  sources?: Evidence[];
  index_version?: string;
  mode?: RetrievalMode;
  detail?: unknown;
};

// sessionStorage is scoped to this browser tab and survives route changes/reloads.
// No DeepSeek credentials or backend secrets are stored in the browser.
const SEARCH_SESSION_KEY = 'governed-rag-search:v1';
type SavedSearch = {
  apiUrl: string;
  query: string;
  retrieval: RetrievalMode;
  responseMode: ResponseMode;
  facets: SelectedFacets;
  includeArchived: boolean;
  showFilters: boolean;
  items: Evidence[];
  answer: string;
  actualMode: string;
  version: string;
  hasSearched?: boolean;
  lastSubmittedFilterSignature?: string;
};

function errorMessage(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object') return JSON.stringify(detail);
  return 'The API returned an error.';
}

// The current index stores a document URL and heading text separately, rather
// than an exact heading ID. Match Docusaurus's common auto-generated IDs as a
// best-effort fallback. Explicit IDs and duplicate headings require an anchor
// stored by the indexing pipeline for guaranteed precision.
function sourceUrl(item: Evidence): string {
  if (!item.heading || item.url.includes('#')) return item.url;
  const slug = item.heading
    .replace(/<[^>]*>/g, '')
    .replace(/\{#[^}]+\}\s*$/, '')
    .trim()
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\p{M}_\-\s]/gu, '')
    .replace(/\s/g, '-');
  return slug ? `${item.url}#${encodeURIComponent(slug)}` : item.url;
}

function remarkEvidenceCitations({sources}: {sources: Evidence[]}) {
  return (tree: Root) => {
    function walk(node: Nodes) {
      if (!('children' in node) || node.type === 'link' || node.type === 'linkReference') return;
      for (let index = 0; index < node.children.length; index++) {
        const child = node.children[index];
        if (child.type !== 'text') {
          walk(child);
          continue;
        }
        const parts: PhrasingContent[] = [];
        let offset = 0;
        for (const match of child.value.matchAll(/\[(\d+)\]/g)) {
          const number = Number(match[1]);
          if (number < 1 || number > sources.length) continue;
          if (match.index > offset) parts.push({type: 'text', value: child.value.slice(offset, match.index)});
          parts.push({type: 'link', url: sourceUrl(sources[number - 1]), children: [{type: 'text', value: match[0]}]});
          offset = match.index + match[0].length;
        }
        if (!parts.length) continue;
        if (offset < child.value.length) parts.push({type: 'text', value: child.value.slice(offset)});
        // Only text children are replaced, so their parent accepts phrasing content.
        node.children.splice(index, 1, ...parts);
        index += parts.length - 1;
      }
    }
    walk(tree);
  };
}

function isMissingDeepSeekKey(detail: unknown): boolean {
  return typeof detail === 'string' &&
    /deepseek_api_key\s+not\s+configured|deepseek.*(?:not configured|disabled|unavailable)/i.test(detail);
}

// Compare the actual facet arrays and archived toggle used by the last successful
// request. Sorting ensures changes to selection order do not trigger a warning.
function filterSignature(selected: SelectedFacets, includeArchived: boolean): string {
  return JSON.stringify({
    includeArchived,
    facets: FACETS.map(({key}) => [key, [...(selected[key] ?? [])].sort()]),
  });
}

export function GovernedSearchExperience({embedded = false}: {embedded?: boolean} = {}): React.JSX.Element {
  const {siteConfig} = useDocusaurusContext();
  // This URL is public configuration, not a secret. DeepSeek keys stay in FastAPI.
  const apiUrl = String(siteConfig.customFields?.ragApiUrl || '').replace(/\/+$/, '');
  const taxonomy = LOCAL_TAXONOMY;
  const [query, setQuery] = useState('');
  const [retrieval, setRetrieval] = useState<RetrievalMode>('hybrid');
  const [responseMode, setResponseMode] = useState<ResponseMode>('search');
  const [facets, setFacets] = useState<SelectedFacets>({});
  const [includeArchived, setIncludeArchived] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [items, setItems] = useState<Evidence[]>([]);
  const [answer, setAnswer] = useState('');
  const [actualMode, setActualMode] = useState<string>('');
  const [version, setVersion] = useState('');
  const [hasSearched, setHasSearched] = useState(false);
  const [lastSubmittedFilterSignature, setLastSubmittedFilterSignature] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  // Avoid overwriting a saved search with the default React state on first mount.
  const [sessionRestored, setSessionRestored] = useState(false);

  useEffect(() => {
    try {
      const raw = window.sessionStorage.getItem(SEARCH_SESSION_KEY);
      if (raw) {
        const saved: Partial<SavedSearch> = JSON.parse(raw);
        if (typeof saved.query === 'string') setQuery(saved.query.slice(0, 500));
        if (saved.retrieval === 'bm25' || saved.retrieval === 'semantic' || saved.retrieval === 'hybrid') {
          setRetrieval(saved.retrieval);
        }
        if (saved.responseMode === 'search' || saved.responseMode === 'chat') {
          setResponseMode(saved.responseMode);
        }
        if (saved.facets && typeof saved.facets === 'object' && !Array.isArray(saved.facets)) {
          // Migrate previous single-select sessions (string) to multi-select arrays.
          // JSON data is untrusted; ignore values that are not non-empty strings.
          const savedSelections = saved.facets as Partial<Record<FacetKey, string | string[]>>;
          const validFacets: SelectedFacets = {};
          for (const {key} of FACETS) {
            const value = savedSelections[key];
            const terms = Array.isArray(value) ? value : typeof value === 'string' ? [value] : [];
            const selected = [...new Set(terms.filter((term): term is string =>
              typeof term === 'string' && Object.prototype.hasOwnProperty.call(LOCAL_TAXONOMY.dimensions[key]?.terms ?? {}, term)))];
            if (selected.length > 0) validFacets[key] = selected;
          }
          setFacets(validFacets);
        }
        if (typeof saved.includeArchived === 'boolean') setIncludeArchived(saved.includeArchived);
        if (typeof saved.showFilters === 'boolean') setShowFilters(saved.showFilters);
        // Do not display results from a different configured backend.
        if (saved.apiUrl === apiUrl) {
          if (Array.isArray(saved.items)) {
            setItems(saved.items.filter((item): item is Evidence =>
              !!item && typeof item === 'object' &&
              typeof item.title === 'string' && typeof item.url === 'string'
            ).slice(0, 20));
          }
          if (typeof saved.answer === 'string') setAnswer(saved.answer.slice(0, 30000));
          if (typeof saved.actualMode === 'string') setActualMode(saved.actualMode);
          if (typeof saved.version === 'string') setVersion(saved.version);
          if (typeof saved.hasSearched === 'boolean') setHasSearched(saved.hasSearched);
          if (typeof saved.lastSubmittedFilterSignature === 'string') {
            setLastSubmittedFilterSignature(saved.lastSubmittedFilterSignature);
          }
        }
      }
    } catch {
      // Browser privacy settings or malformed old data must never break the page.
    } finally {
      setSessionRestored(true);
    }
  }, [apiUrl]);

  useEffect(() => {
    if (!sessionRestored) return;
    try {
      const saved: SavedSearch = {
        apiUrl, query, retrieval, responseMode, facets, includeArchived, showFilters,
        items, answer, actualMode, version, hasSearched,
        ...(lastSubmittedFilterSignature !== null ? {lastSubmittedFilterSignature} : {}),
      };
      window.sessionStorage.setItem(SEARCH_SESSION_KEY, JSON.stringify(saved));
    } catch {
      // Quota restrictions/private browsing: search continues without persistence.
    }
  }, [sessionRestored, apiUrl, query, retrieval, responseMode, facets,
    includeArchived, showFilters, items, answer, actualMode, version, hasSearched,
    lastSubmittedFilterSignature]);

  function toggleFacet(key: FacetKey, term: string) {
    setFacets((current) => {
      const selected = current[key] ?? [];
      const next = selected.includes(term)
        ? selected.filter((item) => item !== term)
        : [...selected, term];
      return {...current, [key]: next};
    });
  }

  function resetFilters() {
    setFacets({});
    setIncludeArchived(false);
    // Preserve query, retrieval mode, results and saved session.
    // Filters take effect on the next submitted search.
  }

  function clearSearch() {
    try {
      window.sessionStorage.removeItem(SEARCH_SESSION_KEY);
    } catch {
      // Search controls still reset even if browser storage is disabled.
    }
    setQuery('');
    setRetrieval('hybrid');
    setResponseMode('search');
    setFacets({});
    setIncludeArchived(false);
    setShowFilters(false);
    setItems([]);
    setAnswer('');
    setActualMode('');
    setVersion('');
    setHasSearched(false);
    setLastSubmittedFilterSignature(null);
    setError('');
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiUrl || query.trim().length < 2 || busy) return;
    setBusy(true); setError(''); setItems([]); setAnswer(''); setActualMode(''); setVersion(''); setHasSearched(false);
    const filters: Record<string, string[]> = {};
    for (const {key} of FACETS) {
      const selected = facets[key] ?? [];
      if (selected.length > 0) filters[key] = [...selected];
    }
    try {
      const response = await fetch(`${apiUrl}/${responseMode}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({query: query.trim(), top_k: 5, mode: retrieval,
          filters, include_archived: includeArchived}),
      });
      const data: ApiResponse = await response.json();
      if (!response.ok) {
        if (response.status === 429) {
          const seconds = response.headers.get('Retry-After');
          throw new Error(seconds
            ? `Search limit reached. Please retry in ${seconds} seconds.`
            : 'Search limit reached. Please try again shortly.');
        }
        if (response.status === 503 && String(data.detail ?? '').includes('Search capacity reached')) {
          throw new Error('The search service is busy. Please try again shortly.');
        }
        if (responseMode === 'chat' && (isMissingDeepSeekKey(data.detail) || String(data.detail ?? '').includes('AI answers are not available'))) {
          throw new Error('AI answers are not available because DeepSeek is not configured. Choose Sources to view matching passages without AI generation.');
        }
        throw new Error(errorMessage(data.detail));
      }
      setItems(responseMode === 'chat' ? (data.sources || []) : (data.results || []));
      setAnswer(data.answer || '');
      setActualMode(data.mode || retrieval);
      setVersion(data.index_version || '');
      setHasSearched(true);
      setLastSubmittedFilterSignature(filterSignature(facets, includeArchived));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed. Check Docker and the API URL.');
    } finally {
      setBusy(false);
    }
  }

  const activeFilters = FACETS.flatMap(({key, label}) =>
    (facets[key] ?? []).map(value => ({key, label, value})));
  const filtersNeedRefresh = hasSearched && lastSubmittedFilterSignature !== null &&
    lastSubmittedFilterSignature !== filterSignature(facets, includeArchived);
  const savedResultsUnverified = hasSearched && lastSubmittedFilterSignature === null;
  const modeLabel = (mode: string) => mode === 'bm25' ? 'Keyword / BM25' : mode === 'semantic' ? 'Semantic / FAISS' : 'Hybrid / both';

  const Container = embedded ? 'div' : 'main';
  const content = (
    <Container className={`${styles.page} ${embedded ? styles.embeddedPage : ''}`}>
      {!embedded && (
        <header className={styles.hero} aria-labelledby="rag-page-title">
          <p className={styles.eyebrow}>Governed taxonomy</p>
          <Heading as="h1" id="rag-page-title" className={styles.heroTitle}>Search knowledge</Heading>
          <p className={styles.intro}>
            Search portfolio content using keywords, concepts or questions.
            Refine results using the governed taxonomy and explore the original source documents.
          </p>
        </header>
      )}

      <div className={styles.workspace}>
        <form onSubmit={submit} className={styles.form} aria-label="Search portfolio knowledge">
            <div className={styles.searchTopline}>
              <label className={styles.fieldLabel} htmlFor="rag-query">What would you like to search?</label>
              <span className={styles.characterCount}>{query.length}/500</span>
            </div>
            <textarea
              id="rag-query" rows={3} maxLength={500} value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="e.g. How is documentation governance enforced?"
              className={styles.query}
              aria-describedby="rag-startup-note"
            />
            <aside id="rag-startup-note" className={styles.startupNote}>
              <i className="fa-solid fa-moon" aria-hidden="true" />
              <div>
                <strong>First search may take longer</strong>
                <p>To keep costs low, the search service sleeps when idle. Your first search wakes it up; subsequent searches are usually faster.</p>
              </div>
            </aside>
            <div className={styles.formOptions}>
              <fieldset className={styles.group}>
                <legend>Search method</legend>
                <div className={styles.segmented}>
                  {(['bm25', 'semantic', 'hybrid'] as RetrievalMode[]).map(mode => (
                    <label className={`${styles.segment} ${retrieval === mode ? styles.segmentActive : ''}`} key={mode}>
                      <input name="rag-retrieval" type="radio" checked={retrieval === mode}
                        onChange={() => setRetrieval(mode)} />
                      {mode === 'bm25' ? 'Keywords' : mode === 'semantic' ? 'Semantic' : 'Hybrid'}
                    </label>
                  ))}
                </div>
              </fieldset>
              <fieldset className={styles.group}>
                <legend>Output</legend>
                <div className={styles.segmented}>
                  <label className={`${styles.segment} ${responseMode === 'search' ? styles.segmentActive : ''}`}>
                    <input name="rag-response" type="radio" checked={responseMode === 'search'}
                      onChange={() => setResponseMode('search')} />
                    Sources
                  </label>
                  <label className={`${styles.segment} ${responseMode === 'chat' ? styles.segmentActive : ''}`}>
                    <input name="rag-response" type="radio" checked={responseMode === 'chat'}
                      onChange={() => setResponseMode('chat')} />
                    AI answer
                  </label>
                </div>
              </fieldset>
            </div>
            {responseMode === 'chat' && (
              <p className={styles.privacyNote} role="note">
                AI-generated answers can be inaccurate, incomplete or misleading.
                Always check the linked source documents before relying on an answer.
              </p>
            )}
            <div className={styles.actions}>
              <button type="submit" className={`button button--primary ${styles.submitButton}`}
                disabled={busy || query.trim().length < 2 || !apiUrl}>
                {busy ? 'Searching…' : responseMode === 'chat' ? 'Generate answer ↗' : 'Search portfolio ↗'}
              </button>
              <button type="button" className={styles.clearButton} onClick={clearSearch} disabled={busy}>
                Clear saved search
              </button>
            </div>
            <p className={styles.privacyNote}>
              Your search and results are saved only in this browser tab. Search again to refresh previously saved results.
            </p>
          </form>

          <aside className={`${styles.filterPanel} ${browseStyles.filters}`} aria-label="Taxonomy filters">
            <div className={browseStyles.filterHeader}>
              <h2>Filter</h2>
              <button type="button" className={browseStyles.clearButton}
                onClick={resetFilters} disabled={busy || (activeFilters.length === 0 && !includeArchived)}>
                Clear filters
              </button>
            </div>
            <div className={styles.toolbar}>
              <button type="button" className={browseStyles.mobileFiltersToggle} aria-expanded={showFilters}
                aria-controls="rag-taxonomy-filters" onClick={() => setShowFilters(v => !v)}>
                {showFilters ? 'Hide filters' : 'Show filters'}
                {activeFilters.length > 0 ? ` (${activeFilters.length} selected)` : ''}
              </button>
            </div>
            <div id="rag-taxonomy-filters" className={`${browseStyles.filterGroups} ${showFilters ? browseStyles.filterGroupsOpen : ''}`}>
                <ExploreTaxonomyFilterGroups
                  disabled={busy}
                  isSelected={(dimensionId, termId) => {
                    const key = navigationTaxonomy.dimensions[dimensionId].metadataField as FacetKey;
                    return (facets[key] ?? []).includes(termId);
                  }}
                  onToggle={(dimensionId, termId) => {
                    const key = navigationTaxonomy.dimensions[dimensionId].metadataField as FacetKey;
                    toggleFacet(key, termId);
                  }}
                />
                <label className={styles.archivedOption}>
                  <input type="checkbox" checked={includeArchived} disabled={busy}
                    onChange={e => setIncludeArchived(e.target.checked)} />
                  Include archived content when lifecycle is not explicitly filtered
                </label>
            </div>
            {activeFilters.length > 0 && (
              <div className={styles.activeFilters} aria-label="Active taxonomy filters">
                {activeFilters.map(({key, label, value}) => (
                  <button key={`${key}:${value}`} type="button" className={styles.activeFilter}
                    title={`Remove ${label}: ${taxonomy?.dimensions[key]?.terms[value] || value}`}
                    disabled={busy}
                    onClick={() => toggleFacet(key, value)}>
                    {label}: {taxonomy?.dimensions[key]?.terms[value] || value} <span aria-hidden="true">×</span>
                  </button>
                ))}
              </div>
            )}
            <p className={styles.toolbarHint}>
              Filters apply on your next search. Search excludes archived passages by default;
              Browse includes archived catalogue documents.
            </p>
          </aside>

          <div className={styles.output}>
          {(filtersNeedRefresh || savedResultsUnverified) && (
            <p className={styles.filterUpdateNotice} role="status" aria-live="polite">
              {filtersNeedRefresh
                ? 'Filters changed — search again to update these results.'
                : 'These saved results may not reflect the current filters. Search again to refresh them.'}
            </p>
          )}
          {!apiUrl && <div role="alert" className={styles.error}>No RAG API URL configured for this site build.</div>}
          {error && (
            <div role="alert" className={styles.error}>
              <p>{error}</p>
              {responseMode === 'chat' && error.startsWith('AI answers are not available') && (
                <button type="button" className="button button--secondary button--sm"
                  onClick={() => {setResponseMode('search'); setError('');}}>
                  Switch to Sources
                </button>
              )}
            </div>
          )}

          {busy && (
            <div className={styles.loading} role="status" aria-live="polite">
              <span className={styles.loadingDot} aria-hidden="true" />
              Searching indexed knowledge…
            </div>
          )}

          {answer && (
            <section className={styles.answer} aria-label="Grounded answer">
              <div className={styles.sectionEyebrow}>EVIDENCE-GROUNDED RESPONSE</div>
              <Heading as="h2" className={styles.sectionTitle}>Synthesised answer</Heading>
              <div className={`${styles.markdown} markdown`}>
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, [remarkEvidenceCitations, {sources: items}]]}
                  components={{a: ({node, ...props}) => <a {...props} target="_blank" rel="noopener noreferrer" />}}
                  skipHtml>{answer}</ReactMarkdown>
              </div>
              <p className={styles.small}>Select a citation marker to open its source or matched section in a new tab.</p>
            </section>
          )}

          {hasSearched && !busy && (
            <section className={styles.results} aria-live="polite" aria-label="Search results">
              <div className={styles.resultsHeader}>
                <div>
                  <div className={styles.sectionEyebrow}>RETRIEVAL OUTPUT</div>
                  <Heading as="h2" className={styles.sectionTitle}>
                    {responseMode === 'chat' ? 'Evidence sources' : 'Search results'}
                  </Heading>
                </div>
                <span className={styles.resultCount}>{items.length} {items.length === 1 ? 'result' : 'results'}</span>
              </div>
              <div className={styles.resultMeta}>
                <span>{modeLabel(actualMode || retrieval)}</span>
                {version && <span title={version}>Index: {version.length > 26 ? `${version.slice(0, 26)}…` : version}</span>}
                <span>Ranked evidence</span>
              </div>
              {items.length === 0 ? (
                <div className={styles.emptyState}>
                  <strong>No matching passages</strong>
                  <p>Try a broader question, another retrieval method or fewer taxonomy filters.</p>
                </div>
              ) : (
                <ol className={styles.resultList}>
                  {items.map((item, index) => (
                    <li className={styles.result} key={`${item.id ?? item.url}-${index}`}>
                      <article>
                        <div className={styles.cardTop}>
                          <span className={styles.rank}>SOURCE {String(index + 1).padStart(2, '0')}</span>
                          <a className={styles.sourceLink} href={sourceUrl(item)} target="_blank" rel="noopener noreferrer">
                            {item.heading?.trim() ? 'Open matched section' : 'Open source'} <span aria-hidden="true">↗</span>
                          </a>
                        </div>
                        {item.heading?.trim() && <p className={styles.parentTitle}>{item.title}</p>}
                        <h3 className={styles.resultTitle}>
                          <a href={sourceUrl(item)} target="_blank" rel="noopener noreferrer">
                            {item.heading?.trim() || item.title}
                          </a>
                        </h3>
                        {item.text && (
                          <details className={styles.snippetDetails}>
                            <summary className={styles.snippetSummary}>
                              <span className={styles.snippetPreview}>{item.text.replace(/[#*_`~>|\[\]]/g, '').replace(/\s+/g, ' ').slice(0, 280)}{item.text.length > 280 ? '…' : ''}</span>
                              <span className={styles.expandText}>
                                <span className={styles.collapsedLabel}>Read full passage</span>
                                <span className={styles.expandedLabel}>Collapse passage</span>
                              </span>
                            </summary>
                            <div className={`${styles.markdown} ${styles.fullPassage} markdown`}>
                              <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml>{item.text}</ReactMarkdown>
                            </div>
                          </details>
                        )}
                        {item.facets && (
                          <div className={styles.tags}>
                            {Object.entries(item.facets)
                              .filter(([key]) => key === 'type' || key === 'lifecycle' || key === 'topics' || key === 'technologies')
                              .flatMap(([key, values]) => values.slice(0, 3).map(value => ({key, value})))
                              .slice(0, 6)
                              .map(({key, value}) => (
                                <span key={`${key}:${value}`} className={styles.tag}>
                                  {taxonomy?.dimensions[key]?.terms[value] || value.replace(/-/g, ' ')}
                                </span>
                              ))}
                          </div>
                        )}
                        <div className={styles.cardFooter}>
                          {typeof item.score === 'number' && (
                            <span className={styles.score} title="Raw retrieval rank score; not a confidence percentage">
                              Rank score {item.score.toFixed(4)}
                            </span>
                          )}
                        </div>
                      </article>
                    </li>
                  ))}
                </ol>
              )}
            </section>
          )}
          {!hasSearched && !busy && !error && (
            <div className={styles.welcome}>
              <div className={styles.welcomeIcon} aria-hidden="true">⌕</div>
              <div>
                <strong>Start with a question.</strong>
                <p>Search the portfolio by concept, technology or documentation practice. Results link to their original source.</p>
              </div>
            </div>
          )}
          <details className={styles.howWorks}>
            <summary>How search works</summary>
            <p>
              Search uses the governed taxonomy and BM25, FAISS or hybrid retrieval.
              Optional AI answers are grounded in linked source passages.
            </p>
          </details>
          </div>
        </div>
    </Container>
  );

  return embedded ? content : (
    <Layout title="Search knowledge" description="Search portfolio content using keyword, semantic and hybrid retrieval, with optional AI-generated answers linked to sources">
      {content}
    </Layout>
  );
}

// Legacy RAG plugin route: only the Explore tab renders the search experience.
export default function GovernedSearchPage(): React.JSX.Element {
  const exploreUrl = useBaseUrl('/explore');
  return <Redirect to={`${exploreUrl}?view=ai-search`} />;
}
