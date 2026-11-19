import React from 'react';
import useBrokenLinks from '@docusaurus/useBrokenLinks';
import Layout from '@theme/Layout';
import styles from './styles.module.css';

type Source = {
  relative: string;
  lines: string[];
  start: number;
  end: number;
};

export default function SourceSnippetPage({source}: {source: Source}): React.ReactElement {
  const {relative, lines, start, end} = source;
  const filename = relative.split('/').at(-1);
  const {collectAnchor} = useBrokenLinks();

  return (
    <Layout title={`Source · ${filename}`}>
      <main className="container margin-vert--lg">
        <h1>{filename}</h1>
        <p><code>{relative}</code> · Lines {start}–{end} shown in the guide</p>
        <pre className={styles.source} aria-label={`Source code for ${relative}`}>
          <code>
            {lines.map((text, index) => {
              const line = index + 1;
              const anchor = `L${line}`;
              collectAnchor(anchor);
              return (
                <span
                  id={anchor}
                  key={line}
                  className={line >= start && line <= end ? styles.excerpt : styles.line}>
                  <a href={`#${anchor}`} aria-label={`Line ${line}`}>{line}</a>{text}
                </span>
              );
            })}
          </code>
        </pre>
      </main>
    </Layout>
  );
}
