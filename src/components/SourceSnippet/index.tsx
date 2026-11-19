import React, {useEffect, useRef, useState} from 'react';
import Link from '@docusaurus/Link';
import CodeBlock from '@theme/CodeBlock';
import styles from './styles.module.css';

type Props = {
  code: string;
  filename: string;
  language?: string;
  sourceUrl: string;
};

export default function SourceSnippet({code, filename, language, sourceUrl}: Props): React.ReactElement {
  const [status, setStatus] = useState<'idle' | 'copied' | 'failed'>('idle');
  const reset = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(reset.current), []);

  async function copyCode() {
    window.clearTimeout(reset.current);
    try {
      await navigator.clipboard.writeText(code);
      setStatus('copied');
      reset.current = window.setTimeout(() => setStatus('idle'), 2000);
    } catch {
      setStatus('failed');
    }
  }

  return (
    <div className={styles.snippet}>
      <div className={styles.header}>
        <code className={styles.filename}>{filename}</code>
        <div className={styles.actions}>
          <Link className={styles.action} to={sourceUrl}>View source</Link>
          <button className={styles.action} type="button" onClick={copyCode}>
            {status === 'copied' ? 'Copied' : 'Copy code'}
          </button>
        </div>
      </div>
      <div className={styles.code}>
        <CodeBlock language={language}>{code}</CodeBlock>
      </div>
      <p className={status === 'failed' ? styles.notice : 'sr-only'} role="status">
        {status === 'copied' && 'Code copied to clipboard.'}
        {status === 'failed' && 'Clipboard access failed. Select and copy the code directly.'}
      </p>
    </div>
  );
}
