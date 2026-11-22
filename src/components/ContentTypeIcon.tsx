import React from 'react';

const paths: Readonly<Partial<Record<string, string>>> = {
  'case-study': 'M3 7h18v13H3z M8 7V4h8v3 M3 12h18 M10 12v2h4v-2',
  'doc-sample': 'M6 3h8l4 4v14H6z M14 3v5h4 M9 12h6 M9 16h6',
  'landing-page': 'M3 4h18v16H3z M3 8h18 M7 12h5v4H7z M15 12h3 M15 16h3',
  'skill': 'M12 3l2.7 5.5 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z',
  'tool': 'M20.5 8.5a5 5 0 0 1-6.7 4.7l-6.5 6.5a2 2 0 0 1-2.8-2.8l6.5-6.5a5 5 0 0 1 5.9-6.5l-3 3 2.8 2.8 3-3a5 5 0 0 1 .8 1.8z',
  'implementation-guide': 'M4 6l1.5 1.5L8 5 M11 6h9 M4 12l1.5 1.5L8 11 M11 12h9 M4 18l1.5 1.5L8 17 M11 18h9',
  'reference-material': 'M12 6c-2-2-5-2-9-2v15c4 0 7 0 9 2 2-2 5-2 9-2V4c-4 0-7 0-9 2zm0 0v15',
  'technical-explanation': 'M9 3h6v5H9z M3 16h6v5H3z M15 16h6v5h-6z M12 8v4 M6 16v-4h12v4',
};

export default function ContentTypeIcon({type}: {type: string}): React.JSX.Element | null {
  const path = paths[type];
  if (!path) return null;

  return (
    <svg aria-hidden="true" focusable="false" width="1em" height="1em" viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d={path} />
    </svg>
  );
}
