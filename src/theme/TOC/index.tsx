import React, {useId, useLayoutEffect, useRef, useState} from 'react';
import clsx from 'clsx';
import {useLocation} from '@docusaurus/router';
import {useStorageSlot} from '@docusaurus/theme-common';
import OriginalTOC from '@theme-original/TOC';
import type {Props} from '@theme/TOC';
import styles from './styles.module.css';

export default function TOC({className, ...props}: Props): React.JSX.Element {
  const contentId = useId();
  const {pathname} = useLocation();
  const navigation = useRef<HTMLElement>(null);
  const [preference, storage] = useStorageSlot('portfolio.heading-navigation', {persistence: 'localStorage'});
  const [fallback, setFallback] = useState(false);
  const collapsed = preference === null ? fallback : preference === 'collapsed';

  useLayoutEffect(() => {
    const column = navigation.current?.parentElement;
    const row = column?.parentElement;
    const article = column?.previousElementSibling;
    if (!collapsed || !column?.matches('.col:last-child') || !row?.classList.contains('row')
      || !(article instanceof HTMLElement) || !article.classList.contains('col')) return;

    row.setAttribute('data-heading-nav-collapsed', '');
    // The docs layout applies an important 75% width cap to this column.
    const previousMaxWidth = article.style.getPropertyValue('max-width');
    const previousPriority = article.style.getPropertyPriority('max-width');
    article.style.setProperty('max-width', '100%', 'important');
    return () => {
      row.removeAttribute('data-heading-nav-collapsed');
      article.style.setProperty('max-width', previousMaxWidth, previousPriority);
    };
  }, [collapsed]);

  useLayoutEffect(() => {
    const nav = navigation.current;
    const column = nav?.parentElement;
    const article = column?.previousElementSibling;
    const actions = article?.querySelector('[data-markdown-page-actions]');
    if (!nav || !column || !article || !actions) return;

    const alignWithActions = () => {
      const offset = actions.getBoundingClientRect().top - column.getBoundingClientRect().top;
      nav.style.setProperty('--heading-nav-offset', `${Math.max(0, offset)}px`);
    };

    const observer = new ResizeObserver(alignWithActions);
    observer.observe(article);
    observer.observe(actions);
    alignWithActions();
    return () => {
      observer.disconnect();
      nav.style.removeProperty('--heading-nav-offset');
    };
  }, [pathname, collapsed]);

  return (
    <nav ref={navigation} className={clsx(styles.navigation, className)} data-collapsed={collapsed || undefined} aria-label="On this page">
      <button
        type="button"
        className={clsx('clean-btn', styles.toggle)}
        title={collapsed ? 'Show page headings' : 'Hide page headings'}
        aria-expanded={!collapsed}
        aria-controls={contentId}
        onClick={() => {
          setFallback(!collapsed);
          storage.set(collapsed ? 'expanded' : 'collapsed');
        }}
      >
        <span className={collapsed ? 'sr-only' : undefined}>On this page</span>
        <span className={styles.chevron} aria-hidden="true" />
      </button>
      <div id={contentId} className={clsx(styles.headings, 'thin-scrollbar')} hidden={collapsed}>
        <OriginalTOC {...props} className={styles.items} />
      </div>
    </nav>
  );
}
