import React, {useState} from 'react';
import styles from './styles.module.css';

const API = 'http://localhost:8000'; // Local-only MVP; do not ship as a production URL.

type Source = {id?: number; title: string; url: string; heading?: string; score?: number; text?: string};

export default function KnowledgeAssistant(): React.JSX.Element {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'search' | 'chat'>('search');
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState<Source[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault(); if (query.trim().length < 2) return;
    setBusy(true); setError(''); setAnswer(''); setSources([]);
    try {
      const response = await fetch(`${API}/${mode}`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({query: query.trim(), top_k: 5}),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'API error');
      if (mode === 'chat') {setAnswer(data.answer ?? ''); setSources(data.sources ?? []);}
      else {setSources(data.results ?? []);}
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed. Is the local API running?');
    } finally {setBusy(false);}
  }

  return <section className={styles.root} aria-label="Local knowledge assistant">
    <p className={styles.notice}>Local development preview. Start the Docker API at localhost:8000.</p>
    <form onSubmit={submit} className={styles.form}>
      <label htmlFor="portfolio-knowledge-query">Question about this portfolio</label>
      <textarea id="portfolio-knowledge-query" value={query} onChange={e => setQuery(e.target.value)}
        maxLength={500} rows={3} placeholder="Which projects demonstrate API governance?" />
      <div className={styles.actions}>
        <label><input type="radio" name="knowledge-mode" checked={mode==='search'} onChange={()=>setMode('search')}/> Search evidence</label>
        <label><input type="radio" name="knowledge-mode" checked={mode==='chat'} onChange={()=>setMode('chat')}/> DeepSeek answer</label>
        <button type="submit" disabled={busy || query.trim().length<2}>{busy ? 'Searching…' : 'Ask'}</button>
      </div>
    </form>
    {error && <p role="alert" className={styles.error}>{error}</p>}
    {answer && <article className={styles.answer}><h3>Answer</h3><p className={styles.pre}>{answer}</p></article>}
    {sources.length>0 && <div aria-live="polite"><h3>{mode==='chat'?'Cited sources':'Retrieved evidence'}</h3>
      <ol>{sources.map((s,i)=><li key={`${s.url}-${i}`}><a href={s.url}>{s.title}</a>
        {s.heading ? ` — ${s.heading}` : ''}{s.text ? <p className={styles.excerpt}>{s.text.slice(0,350)}…</p> : null}</li>)}</ol>
    </div>}
  </section>;
}
