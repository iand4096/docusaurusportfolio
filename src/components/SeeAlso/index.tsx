import React from 'react';
import Link from '@docusaurus/Link';
import Heading from '@theme/Heading';
import {usePluginData} from '@docusaurus/useGlobalData';
import styles from './styles.module.css';

type RelatedLink = {id: string; title: string; path: string};

export default function SeeAlso({permalink}: {permalink: string}): React.JSX.Element | null {
  const data = usePluginData('see-also') as {byPath: Record<string, RelatedLink[]>};
  const links = data.byPath[permalink];
  if (!links?.length) return null;
  return (
    <section className={styles.seeAlso} aria-label="See also">
      <Heading as="h2">See also</Heading>
      <ul>
        {links.map(link => <li key={link.id}><Link to={link.path}>{link.title}</Link></li>)}
      </ul>
    </section>
  );
}
