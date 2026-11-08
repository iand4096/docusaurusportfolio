import React, {useEffect, useState} from 'react';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import styles from './styles.module.css';

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
};

function errorMessage(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object') return JSON.stringify(detail);
  return 'The API returned an error.';
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
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [taxonomyError, setTaxonomyError] = useState('');
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
        items, answer, actualMode, version,
      };
      window.sessionStorage.setItem(SEARCH_SESSION_KEY, JSON.stringify(saved));
    } catch {
      // Quota restrictions/private browsing: search continues without persistence.
    }
  }, [sessionRestored, apiUrl, query, retrieval, responseMode, facets,
    includeArchived, showFilters, items, answer, actualMode, version]);

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
    setError('');
  }

  useEffect(() => {
    if (!apiUrl) return;
    const controller = new AbortController();
    fetch(`${apiUrl}/taxonomy`, {signal: controller.signal})
      .then(async response => {
        const data = await response.json();
        if (!response.ok) throw new Error(errorMessage(data.detail));
        setTaxonomy(data as TaxonomyResponse);
      })
      .catch(err => {
        if (controller.signal.aborted) return;
        setTaxonomyError(err instanceof Error ? err.message : 'Could not load taxonomy');
      });
    return () => controller.abort();
  }, [apiUrl]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiUrl || query.trim().length < 2 || busy) return;
    setBusy(true); setError(''); setItems([]); setAnswer(''); setActualMode(''); setVersion('');
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
      if (!response.ok) throw new Error(errorMessage(data.detail));
      setItems(responseMode === 'chat' ? (data.sources || []) : (data.results || []));
      setAnswer(data.answer || '');
      setActualMode(data.mode || retrieval);
      setVersion(data.index_version || '');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed. Check Docker and the API URL.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <Layout title="AI knowledge search" description="Search the portfolio's governed technical knowledge">
      <main className="container margin-vert--lg">
        <div className={styles.page}>
          <Heading as="h1">AI knowledge search</Heading>
          <p className={styles.intro}>Explore the portfolio with governed taxonomy filters, keyword search, semantic search, or both. You can also request an evidence-grounded DeepSeek answer.</p>
          <form onSubmit={submit} className={styles.form}>
            <label className={styles.fieldLabel} htmlFor="rag-query">Your question</label>
            <textarea id="rag-query" rows={3} maxLength={500} value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="How is documentation governance enforced?" className={styles.query} />
            <fieldset className={styles.group}>
              <legend>Retrieval method</legend>
              {(['bm25', 'semantic', 'hybrid'] as RetrievalMode[]).map(mode => (
                <label className={styles.option} key={mode}>
                  <input name="rag-retrieval" type="radio" checked={retrieval === mode}
                    onChange={() => setRetrieval(mode)} />
                  {mode === 'bm25' ? 'BM25 · keywords' : mode === 'semantic' ? 'FAISS · semantic' : 'Hybrid · both'}
                </label>
              ))}
            </fieldset>
            <fieldset className={styles.group}>
              <legend>Response</legend>
              <label className={styles.option}>
                <input type="radio" name="rag-response" checked={responseMode === 'search'} onChange={() => setResponseMode('search')} />
                Retrieved passages
              </label>
              <label className={styles.option}>
                <input type="radio" name="rag-response" checked={responseMode === 'chat'} onChange={() => setResponseMode('chat')} />
                DeepSeek answer with citations
              </label>
            </fieldset>
            <div className={styles.filtersToggle}>
              <button type="button" className="button button--secondary button--sm" aria-expanded={showFilters}
                onClick={() => setShowFilters(v => !v)}>
                {showFilters ? 'Hide' : 'Show'} taxonomy filters
              </button>
            </div>
            {showFilters && <div className={styles.filters}>
              {FACETS.map(({key, label}) => (
                <label className={styles.filter} key={key}>
                  <span>{label}</span>
                  <select value={facets[key] || ''}
                    onChange={e => setFacets(prev => ({...prev, [key]: e.target.value}))}
                    disabled={!taxonomy?.dimensions[key]}>
                    <option value="">Any</option>
                    {Object.entries(taxonomy?.dimensions[key]?.terms || {})
                      .sort((a, b) => a[1].localeCompare(b[1]))
                      .map(([id, name]) => <option key={id} value={id}>{name}</option>)}
                  </select>
                </label>
              ))}
              <label className={styles.option}>
                <input type="checkbox" checked={includeArchived} onChange={e => setIncludeArchived(e.target.checked)} />
                Include archived content when not explicitly filtered by lifecycle
              </label>
              {taxonomyError && <p className={styles.warning} role="status">Could not load taxonomy options: {taxonomyError}</p>}
            </div>}
            <div className={styles.actions}>
              <button type="submit" className="button button--primary" disabled={busy || query.trim().length < 2 || !apiUrl}>
                {busy ? 'Working…' : responseMode === 'chat' ? 'Generate answer' : 'Search portfolio'}
              </button>
              <button type="button" className="button button--secondary" onClick={clearSearch} disabled={busy}>
                Clear saved search
              </button>
            </div>
            <p className={styles.small}>Your query, filters, results, and answer stay in this browser tab across navigation and reloads. Results are saved snapshots; search again to refresh them.</p>
          </form>
          {!apiUrl && <p role="alert" className={styles.error}>No RAG API URL configured for this site build.</p>}
          {error && <p role="alert" className={styles.error}>{error}</p>}
          {answer && <section className={styles.answer} aria-live="polite">
            <Heading as="h2">Grounded answer</Heading>
            <p className={styles.answerText}>{answer}</p>
            <p className={styles.small}>Citation markers [1], [2], etc. correspond to the sources below.</p>
          </section>}
          {(items.length > 0 || version) && <section className={styles.results} aria-live="polite">
            <Heading as="h2">{responseMode === 'chat' ? 'Evidence sources' : 'Retrieved passages'}</Heading>
            <p className={styles.small}>Retrieval: {actualMode} · Index: {version || 'unknown'} · {items.length} result(s)</p>
            <ol className={styles.resultList}>
              {items.map((item, index) => <li className={styles.result} key={`${item.id ?? item.url}-${index}`}>
                <div><a href={item.url} target="_blank" rel="noopener noreferrer">{item.title}</a>
                  {item.heading ? <span className={styles.heading}> · {item.heading}</span> : null}
                </div>
                {typeof item.score === 'number' && <div className={styles.small}>Retrieval rank score: {item.score.toFixed(6)}</div>}
                {item.text && <p className={styles.excerpt}>{item.text.slice(0, 450)}{item.text.length > 450 ? '…' : ''}</p>}
                {item.facets && <div className={styles.small}>{Object.entries(item.facets)
                  .filter(([key]) => key === 'type' || key === 'lifecycle')
                  .map(([key, values]) => `${key}: ${values.join(', ')}`).join(' · ')}</div>}
              </li>)}
            </ol>
          </section>}
        </div>
      </main>
    </Layout>
  );
}
