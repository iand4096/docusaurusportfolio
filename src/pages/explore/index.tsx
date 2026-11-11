import React, {useEffect, useRef, useState} from 'react';
import Layout from '@theme/Layout';
import {BrowseExperience} from '@site/src/pages/browse/index';
// The install script substitutes the real project path to your existing component.
import {GovernedSearchExperience} from '@site/src/components/GovernedSearch/GovernedSearchPage';
import styles from './styles.module.css';

type ExploreView = 'browse' | 'ai-search';

function viewFromUrl(): ExploreView {
  if (typeof window === 'undefined') return 'browse';
  return new URLSearchParams(window.location.search).get('view') === 'ai-search'
    ? 'ai-search'
    : 'browse';
}

export default function ExplorePage(): React.JSX.Element {
  // Stable SSR default: read the URL after hydration to avoid a mismatch.
  const [view, setView] = useState<ExploreView>('browse');
  // Lazy-mount the API-backed tab, then keep it mounted to preserve state.
  const [searchMounted, setSearchMounted] = useState(false);
  const browseTab = useRef<HTMLButtonElement>(null);
  const aiTab = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const syncFromUrl = () => {
      const next = viewFromUrl();
      setView(next);
      if (next === 'ai-search') setSearchMounted(true);
    };
    syncFromUrl();
    window.addEventListener('popstate', syncFromUrl);
    return () => window.removeEventListener('popstate', syncFromUrl);
  }, []);

  function chooseView(next: ExploreView): void {
    setView(next);
    if (next === 'ai-search') setSearchMounted(true);
    // Use a query parameter rather than replacing Docusaurus routing.
    const url = new URL(window.location.href);
    url.searchParams.set('view', next);
    window.history.pushState(window.history.state, '', `${url.pathname}${url.search}${url.hash}`);
  }

  function handleTabKeys(event: React.KeyboardEvent<HTMLButtonElement>, current: ExploreView): void {
    let next: ExploreView;
    if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
      next = current === 'browse' ? 'ai-search' : 'browse';
    } else if (event.key === 'Home') {
      next = 'browse';
    } else if (event.key === 'End') {
      next = 'ai-search';
    } else {
      return;
    }
    event.preventDefault();
    chooseView(next);
    (next === 'browse' ? browseTab : aiTab).current?.focus();
  }

  return (
    <Layout title="Explore knowledge" description="Browse portfolio content by governed taxonomy or use AI search to find evidence in source documents.">
      <main className={`container margin-vert--lg ${styles.page}`}>
        <header className={styles.header}>
          <p className={styles.eyebrow}>Governed taxonomy</p>
          <h1>Explore knowledge</h1>
          <p className={styles.intro}>
            Browse content by type, topic, technology, audience and lifecycle,
            or search indexed source documents using keywords, concepts and questions.
          </p>
        </header>

        <div className={styles.tabs} role="tablist" aria-label="Explore portfolio knowledge">
          <button ref={browseTab} id="explore-browse-tab" type="button" role="tab"
            aria-selected={view === 'browse'} aria-controls="explore-browse-panel"
            tabIndex={view === 'browse' ? 0 : -1}
            className={`${styles.tab} ${view === 'browse' ? styles.tabSelected : ''}`}
            onClick={() => chooseView('browse')}
            onKeyDown={event => handleTabKeys(event, 'browse')}>
            Browse
          </button>
          <button ref={aiTab} id="explore-ai-tab" type="button" role="tab"
            aria-selected={view === 'ai-search'} aria-controls="explore-ai-panel"
            tabIndex={view === 'ai-search' ? 0 : -1}
            className={`${styles.tab} ${view === 'ai-search' ? styles.tabSelected : ''}`}
            onClick={() => chooseView('ai-search')}
            onKeyDown={event => handleTabKeys(event, 'ai-search')}>
            Search
          </button>
        </div>

        <section id="explore-browse-panel" role="tabpanel" aria-labelledby="explore-browse-tab"
          className={styles.panel} hidden={view !== 'browse'}>
          <BrowseExperience embedded />
        </section>
        <section id="explore-ai-panel" role="tabpanel" aria-labelledby="explore-ai-tab"
          className={styles.panel} hidden={view !== 'ai-search'}>
          {searchMounted && <GovernedSearchExperience embedded />}
        </section>
      </main>
    </Layout>
  );
}
