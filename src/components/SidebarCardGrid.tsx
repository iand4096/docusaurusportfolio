import React from 'react';
import Link from '@docusaurus/Link';
import {useDocsSidebar} from '@docusaurus/plugin-content-docs/client';
import type {PropSidebarItem} from '@docusaurus/plugin-content-docs';

type CardMetadata = {
  tag: string;
  description: string;
  highlights: string[];
  ariaLabel?: string;
};

type Card = {
  title: string;
  href: string;
  metadata: CardMetadata;
};

type Props = {
  metadataKey?: string;
  linkLabel?: string;
  ariaLabelSuffix?: string;
};

function extractCards(
  items: PropSidebarItem[],
  metadataKey: string,
): Card[] {
  return items.flatMap((item) => {
    if (item.type === 'category') {
      return extractCards(item.items, metadataKey);
    }

    if (item.type !== 'link') {
      return [];
    }

    const customProps = item.customProps as
      | Record<string, unknown>
      | undefined;

    const metadata = customProps?.[metadataKey] as
      | CardMetadata
      | undefined;

    if (!metadata) {
      return [];
    }

    return [
      {
        title: item.label,
        href: item.href,
        metadata,
      },
    ];
  });
}

export default function SidebarCardGrid({
  metadataKey = 'skillCard',
  linkLabel = 'Explore →',
  ariaLabelSuffix = '',
}: Props): React.ReactElement | null {
  const sidebar = useDocsSidebar();

  if (!sidebar) {
    return null;
  }

  const cards = extractCards(sidebar.items, metadataKey);

  return (
    <div className="skills-grid">
      {cards.map(({title, href, metadata}) => (
        <Link
          key={href}
          className="skill-card"
          to={href}
          aria-label={
            metadata.ariaLabel ??
            `Explore ${title}${ariaLabelSuffix ? ` ${ariaLabelSuffix}` : ''}`
          }
        >
          <span className="skill-card__tag">
            {metadata.tag}
          </span>

          <h2>{title}</h2>

          <div className="skill-card__description">
            {metadata.description}
          </div>

          <ul className="skill-card__highlights">
            {metadata.highlights.map((highlight) => (
              <li key={highlight}>{highlight}</li>
            ))}
          </ul>

          <span className="skill-card__link">
            {linkLabel}
          </span>
        </Link>
      ))}
    </div>
  );
}