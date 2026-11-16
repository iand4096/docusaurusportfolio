import React, {useEffect, useState} from 'react';
import styles from './BrowseExperience/styles.module.css';

const STORAGE_KEY = 'metadata-filters-visible';
const CHANGE_EVENT = 'metadata-filters-visibility';
let sessionVisible = false;

function readVisible(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === 'true';
  } catch {
    return sessionVisible;
  }
}

/** One visibility preference shared by Browse and AI Search; SSR starts closed. */
export function useMetadataFilterVisibility(): readonly [boolean, () => void] {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    setVisible(readVisible());
    const onChange = (event: Event) => setVisible((event as CustomEvent<boolean>).detail);
    const onStorage = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY || event.key === null) setVisible(readVisible());
    };
    window.addEventListener(CHANGE_EVENT, onChange);
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener(CHANGE_EVENT, onChange);
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  function toggle() {
    const next = !visible;
    sessionVisible = next;
    try {
      window.localStorage.setItem(STORAGE_KEY, String(next));
    } catch {
      // Filtering remains usable when browser storage is blocked.
    }
    window.dispatchEvent(new CustomEvent(CHANGE_EVENT, {detail: next}));
  }
  return [visible, toggle];
}

export default function MetadataFilterToggle({visible, onToggle, controls, count = 0}: {
  visible: boolean; onToggle: () => void; controls: string; count?: number;
}): React.JSX.Element {
  return (
    <button type="button" className={styles.metadataFiltersToggle}
      aria-expanded={visible} aria-controls={controls} onClick={onToggle}
      title="Show or hide metadata filters. This preference is saved in this browser.">
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none"
        stroke="currentColor" strokeWidth="1.7" aria-hidden="true" focusable="false">
        <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" />
        <circle cx="12" cy="12" r="3" />
        {visible && <path d="m3 3 18 18" />}
      </svg>
      <span>{visible ? 'Hide filters' : 'Show filters'}{count > 0 ? ` (${count} selected)` : ''}</span>
    </button>
  );
}
