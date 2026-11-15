import React from 'react';
import layout from '../capability-layout.module.css';
import styles from './styles.module.css';

export default function CapabilityCard({items = []}) {
  return (
    <div className={`${layout.grid} ${styles.cards}`}>
      <ul>
        {items.map(({title, summary, detail, icon}) => (
          <li key={title} className={styles.card}>
            {icon && (
              <i
                className={`fa-solid fa-${icon} ${styles.icon}`}
                aria-hidden="true"
              />
            )}
            <h3 className={styles.title}>{title}</h3>
            <p className={styles.description}>{summary}</p>
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
