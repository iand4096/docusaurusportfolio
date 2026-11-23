import React from 'react';
import layout from '../capability-layout.module.css';
import styles from './styles.module.css';

export default function CapabilityCard({items = [], autoColumns = false, heading: Heading = 'h3'}) {
  const columns = Math.max(1, Math.min(items.length, 3));

  return (
    <div
      className={`${layout.grid} ${styles.cards}`}
      style={autoColumns ? {'--capability-desktop-columns': columns} : undefined}
    >
      <ul>
        {items.map(({title, summary, detail, icon}) => (
          <li key={title} className={styles.card}>
            {icon && (
              <i
                className={`fa-solid fa-${icon} ${styles.icon}`}
                aria-hidden="true"
              />
            )}
            <Heading className={styles.title}>{title}</Heading>
            <div className={styles.description}>{summary}</div>
            {detail && (
              <details className={styles.details}>
                <summary aria-label={`More detail about ${title}`}>
                  More detail
                </summary>
                <p>{detail}</p>
              </details>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
