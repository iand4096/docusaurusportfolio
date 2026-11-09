import React, {useEffect, useState} from 'react';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import styles from './styles.module.css';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

type RetrievalMode = 'bm25' | 'semantic' | 'hybrid';
type ResponseMode = 'search' | 'chat';
type FacetKey = 'type' | 'audiences' | 'topics' | 'technologies' | 'lifecycle';
const FACETS: {key: FacetKey; label: string}[] = [
  {key: 'type', label: 'Content type'},
  {key: 'audiences', label: 'Audience'},
  {key: 'topics', label: 'Topic'},
  {key: 'technologies', label: 'Technology'},
  {key: 'lifecycle', label: 'Lifecycle'},
];

type TaxonomyDimension = {label: string; terms: Record<string, string>};
type TaxonomyResponse = {version: number; dimensions: Record<string, TaxonomyDimension>};
type TaxonomyStatus = 'loading' | 'retrying' | 'ready' | 'error';
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
  facets: Partial<Record<FacetKey, string>>;
  includeArchived: boolean;
  showFilters: boolean;
  items: Evidence[];
  answer: string;
  actualMode: string;
  version: string;
  hasSearched?: boolean;
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

function isMissingDeepSeekKey(detail: unknown): boolean {
  return typeof detail === 'string' &&
    /deepseek_api_key\s+not\s+configured|deepseek.*(?:not configured|disabled|unavailable)/i.test(detail);
}

export default function GovernedSearchPage(): React.JSX.Element {
  const {siteConfig} = useDocusaurusContext();
  // This URL is public configuration, not a secret. DeepSeek keys stay in FastAPI.
  const apiUrl = String(siteConfig.customFields?.ragApiUrl || '').replace(/\/+$/, '');
  const [query, setQuery] = useState('');
  const [retrieval, setRetrieval] = useState<RetrievalMode>('hybrid');
  const [responseMode, setResponseMode] = useState<ResponseMode>('search');
  const [taxonomy, setTaxonomy] = useState<TaxonomyResponse | null>(null);
  const [facets, setFacets] = useState<Partial<Record<FacetKey, string>>>({});
  const [includeArchived, setIncludeArchived] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [items, setItems] = useState<Evidence[]>([]);
  const [answer, setAnswer] = useState('');
  const [actualMode, setActualMode] = useState<string>('');
  const [version, setVersion] = useState('');
  const [hasSearched, setHasSearched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [taxonomyError, setTaxonomyError] = useState('');
  const [taxonomyStatus, setTaxonomyStatus] = useState<TaxonomyStatus>('loading');
  const [taxonomyAttempt, setTaxonomyAttempt] = useState(1);
  const [taxonomyReload, setTaxonomyReload] = useState(0);
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
          const validFacets: Partial<Record<FacetKey, string>> = {};
          for (const {key} of FACETS) {
            if (typeof saved.facets[key] === 'string') validFacets[key] = saved.facets[key];
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
      };
      window.sessionStorage.setItem(SEARCH_SESSION_KEY, JSON.stringify(saved));
    } catch {
      // Quota restrictions/private browsing: search continues without persistence.
    }
  }, [sessionRestored, apiUrl, query, retrieval, responseMode, facets,
    includeArchived, showFilters, items, answer, actualMode, version, hasSearched]);

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
    setError('');
  }

  // A cold-started Container App may take time to respond. Retry transient failures,
  // but don't repeatedly retry client errors (for example 403 from an IP allowlist).
  useEffect(() => {
    if (!apiUrl) {
      setTaxonomy(null);
      setTaxonomyError('No API URL is configured for this site build.');
      setTaxonomyStatus('error');
      return;
    }

    let cancelled = false;
    let activeRequest: AbortController | null = null;
    let delayTimer: ReturnType<typeof setTimeout> | undefined;
    let timeoutTimer: ReturnType<typeof setTimeout> | undefined;
    let resumeDelay: (() => void) | undefined;
    const maxAttempts = 3;
    const retryDelaysMs = [1500, 3500];

    setTaxonomy(null);
    setTaxonomyError('');
    setTaxonomyStatus('loading');
    setTaxonomyAttempt(1);

    async function loadTaxonomy() {
      for (let attempt = 1; attempt <= maxAttempts && !cancelled; attempt++) {
        setTaxonomyAttempt(attempt);
        setTaxonomyStatus(attempt === 1 ? 'loading' : 'retrying');
        const controller = new AbortController();
        activeRequest = controller;
        let shouldRetry = true;

        try {
          // Bound each attempt so a stalled connection doesn't disable filters forever.
          timeoutTimer = setTimeout(() => controller.abort(), 20000);
          const response = await fetch(`${apiUrl}/taxonomy`, {signal: controller.signal});
          if (!response.ok) {
            shouldRetry = response.status === 408 || response.status === 429 || response.status >= 500;
            let message = `Taxonomy API returned HTTP ${response.status}`;
            try {
              const data = await response.json();
              if (data && data.detail) message = `${message}: ${errorMessage(data.detail)}`;
            } catch { /* Error response need not be JSON. */ }
            throw new Error(message);
          }
          const data: TaxonomyResponse = await response.json();
          if (!data || !data.dimensions || typeof data.dimensions !== 'object') {
            shouldRetry = false;
            throw new Error('Taxonomy response has an unexpected format.');
          }
          if (cancelled) return;
          setTaxonomy(data);
          setTaxonomyError('');
          setTaxonomyStatus('ready');
          return;
        } catch (err) {
          if (cancelled) return;
          const message = controller.signal.aborted
            ? 'Taxonomy request timed out.'
            : err instanceof Error ? err.message : 'Could not load taxonomy.';
          if (!shouldRetry || attempt === maxAttempts) {
            setTaxonomyError(message);
            setTaxonomyStatus('error');
            return;
          }
          setTaxonomyStatus('retrying');
          await new Promise<void>(resolve => {
            resumeDelay = resolve;
            delayTimer = setTimeout(() => {
              resumeDelay = undefined;
              resolve();
            }, retryDelaysMs[attempt - 1]);
          });
        } finally {
          if (timeoutTimer !== undefined) clearTimeout(timeoutTimer);
          activeRequest = null;
        }
      }
    }
    void loadTaxonomy();
    return () => {
      cancelled = true;
      activeRequest?.abort();
      if (timeoutTimer !== undefined) clearTimeout(timeoutTimer);
      if (delayTimer !== undefined) clearTimeout(delayTimer);
      resumeDelay?.();
    };
  }, [apiUrl, taxonomyReload]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiUrl || query.trim().length < 2 || busy) return;
    setBusy(true); setError(''); setItems([]); setAnswer(''); setActualMode(''); setVersion(''); setHasSearched(false);
    const filters: Record<string, string[]> = {};
    for (const {key} of FACETS) {
      if (facets[key]) filters[key] = [facets[key]!];
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed. Check Docker and the API URL.');
    } finally {
      setBusy(false);
    }
  }

  const activeFilters = FACETS.filter(({key}) => Boolean(facets[key]));
  const modeLabel = (mode: string) => mode === 'bm25' ? 'Keyword / BM25' : mode === 'semantic' ? 'Semantic / FAISS' : 'Hybrid / both';

  return (
    <Layout title="AI knowledge search" description="Explore governed portfolio knowledge using hybrid retrieval">
      <main className={styles.page}>
        <section className={styles.hero} aria-labelledby="rag-page-title">
          <div className={styles.heroGlow} aria-hidden="true" />
          <div className={styles.heroContent}>
            <span className={styles.eyebrow}><span className={styles.sparkle} aria-hidden="true">✦</span> KNOWLEDGE EXPLORER</span>
            <Heading as="h1" id="rag-page-title" className={styles.heroTitle}>
              Explore ideas. <span className={styles.heroAccent}>Find the evidence.</span>
            </Heading>
            <p className={styles.intro}>
              Search documentation engineering, API design and knowledge governance with
              keyword, semantic and hybrid retrieval.
            </p>
            <div className={styles.heroMeta} aria-label="Search capabilities">
              <span>◇ Governed taxonomy</span>
              <span>◇ BM25 + FAISS</span>
              <span>◇ Source-linked evidence</span>
            </div>
          </div>
        </section>

        <div className={styles.workspace}>
          <form onSubmit={submit} className={styles.form} aria-label="Search portfolio knowledge">
            <div className={styles.searchTopline}>
              <label className={styles.fieldLabel} htmlFor="rag-query">What would you like to explore?</label>
              <span className={styles.characterCount}>{query.length}/500</span>
            </div>
            <textarea
              id="rag-query" rows={3} maxLength={500} value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="e.g. How is documentation governance enforced?"
              className={styles.query}
            />
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
            <div className={styles.toolbar}>
              <button type="button" className={styles.filterButton} aria-expanded={showFilters}
                aria-controls="rag-taxonomy-filters" onClick={() => setShowFilters(v => !v)}>
                <span aria-hidden="true">☷</span> {showFilters ? 'Hide filters' : 'Taxonomy filters'}
                {activeFilters.length > 0 && <span className={styles.filterCount}>{activeFilters.length}</span>}
              </button>
              <button type="button" className={styles.resetFiltersButton}
                onClick={resetFilters} disabled={busy || (activeFilters.length === 0 && !includeArchived)}>
                Reset filters
              </button>
              <span className={styles.toolbarHint} role="status" aria-live="polite">
                {taxonomyStatus === 'loading' && 'Loading taxonomy filters…'}
                {taxonomyStatus === 'retrying' && `Waking API / retrying taxonomy (${taxonomyAttempt}/3)…`}
                {taxonomyStatus === 'ready' && 'Taxonomy filters ready'}
                {taxonomyStatus === 'error' && 'Taxonomy filters unavailable'}
              </span>
            </div>
            {showFilters && (
              <div id="rag-taxonomy-filters" className={styles.filters}>
                {FACETS.map(({key, label}) => (
                  <label className={styles.filter} key={key}>
                    <span>{label}</span>
                    <select value={facets[key] || ''}
                      onChange={e => setFacets(prev => ({...prev, [key]: e.target.value}))}
                      disabled={!taxonomy?.dimensions[key]}>
                      <option value="">All {label.toLowerCase()}</option>
                      {Object.entries(taxonomy?.dimensions[key]?.terms || {})
                        .sort((a, b) => a[1].localeCompare(b[1]))
                        .map(([id, name]) => <option key={id} value={id}>{name}</option>)}
                    </select>
                  </label>
                ))}
                <label className={styles.archivedOption}>
                  <input type="checkbox" checked={includeArchived}
                    onChange={e => setIncludeArchived(e.target.checked)} />
                  Include archived content when lifecycle is not explicitly filtered
                </label>
                {(taxonomyStatus === 'loading' || taxonomyStatus === 'retrying') && (
                  <p className={styles.taxonomyNotice} role="status" aria-live="polite">
                    <span className={styles.loadingDot} aria-hidden="true" />
                    {taxonomyStatus === 'retrying'
                      ? `The API may be starting up. Retrying taxonomy (${taxonomyAttempt} of 3)…`
                      : 'Loading taxonomy options…'}
                  </p>
                )}
                {taxonomyStatus === 'error' && (
                  <div className={styles.taxonomyError} role="alert">
                    <span>Could not load taxonomy filters. {taxonomyError}</span>
                    <button type="button" className="button button--secondary button--sm"
                      disabled={!apiUrl} onClick={() => setTaxonomyReload(n => n + 1)}>
                      Retry loading filters
                    </button>
                  </div>
                )}
              </div>
            )}
            {activeFilters.length > 0 && (
              <div className={styles.activeFilters} aria-label="Active taxonomy filters">
                {activeFilters.map(({key, label}) => (
                  <button key={key} type="button" className={styles.activeFilter}
                    title={`Remove ${label} filter`}
                    onClick={() => setFacets(prev => ({...prev, [key]: ''}))}>
                    {label}: {taxonomy?.dimensions[key]?.terms[facets[key]!] || facets[key]} <span aria-hidden="true">×</span>
                  </button>
                ))}
              </div>
            )}
            <div className={styles.actions}>
              <button type="submit" className={`button button--primary ${styles.submitButton}`}
                disabled={busy || query.trim().length < 2 || !apiUrl}>
                {busy ? 'Searching…' : responseMode === 'chat' ? 'Generate answer ↗' : 'Explore knowledge ↗'}
              </button>
              <button type="button" className={styles.clearButton} onClick={clearSearch} disabled={busy}>
                Clear saved search
              </button>
            </div>
            <p className={styles.privacyNote}>
              Your search and results are saved only in this browser tab. Search again to refresh previously saved results.
            </p>
          </form>

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
                <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml>{answer}</ReactMarkdown>
              </div>
              <p className={styles.small}>Citation markers [1], [2], etc. refer to the evidence sources below.</p>
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
                            Open source <span aria-hidden="true">↗</span>
                          </a>
                        </div>
                        <h3 className={styles.resultTitle}>
                          <a href={sourceUrl(item)} target="_blank" rel="noopener noreferrer">{item.title}</a>
                        </h3>
                        {item.heading && <p className={styles.heading}>{item.heading}</p>}
                        {item.text && (
                          <details className={styles.snippetDetails}>
                            <summary className={styles.snippetSummary}>
                              <span className={styles.snippetPreview}>{item.text.replace(/[#*_`~>|\[\]]/g, '').replace(/\s+/g, ' ').slice(0, 280)}{item.text.length > 280 ? '…' : ''}</span>
                              <span className={styles.expandText}>Read full passage</span>
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
                        {typeof item.score === 'number' && (
                          <div className={styles.score} title="Raw retrieval rank score; not a confidence percentage">
                            Rank score {item.score.toFixed(4)}
                          </div>
                        )}
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
                <p>Explore the knowledge base by concept, technology or documentation practice. Results link to their original source.</p>
              </div>
            </div>
          )}
        </div>
      </main>
    </Layout>
  );
}
