import React from 'react';
import Link from '@docusaurus/Link';
import {getEndpoint} from './operationLinks';
import styles from './styles.module.css';

type ApiEndpointProps = {
  operationId: string;
  variant?: 'inline' | 'standalone';
};

export default function ApiEndpoint({operationId, variant = 'inline'}: ApiEndpointProps): React.JSX.Element {
  const {method, path, fragment, operation: {summary}} = getEndpoint(operationId);
  const standalone = variant === 'standalone';

  return (
    <Link
      className={`no-link-highlight ${styles.endpoint} ${standalone ? styles.standalone : styles.inline}`}
      data-method={method}
      to={`/search-api${fragment}`}>
      <span className={styles.method}>{method.toUpperCase()}</span>{' '}
      <span className={styles.destination}>
        {standalone && summary && <span className={styles.summary}>{summary}</span>}
        <code className={styles.path}>{path}</code>
      </span>
      {standalone && <span className={styles.arrow} aria-hidden="true">→</span>}
    </Link>
  );
}
