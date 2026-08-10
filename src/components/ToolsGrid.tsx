import React from 'react';
import Link from '@docusaurus/Link';
import {useDocsSidebar} from '@docusaurus/plugin-content-docs/client';
import type {PropSidebarItem} from '@docusaurus/plugin-content-docs';

type SkillCardMetadata = {
  tag: string;
  description: string;
  highlights: string[];
  ariaLabel?: string;
};

type SkillCard = {
  title: string;
  href: string;
  metadata: SkillCardMetadata;
};

function extractSkillCards(items: PropSidebarItem[]): SkillCard[] {
  return items.flatMap((item) => {
    // Support nested folders/categories later if you add them.
    if (item.type === 'category') {
      return extractSkillCards(item.items);
    }

    if (item.type !== 'link') {
      return [];
    }

    const metadata = item.customProps?.skillCard as
      | SkillCardMetadata
      | undefined;

    // Documents without skillCard metadata, such as skills/index.md,
    // aren't rendered as cards.
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

export default function ToolsGrid(): React.ReactElement | null {
  const sidebar = useDocsSidebar();

  if (!sidebar) {
    return null;
  }

  const skills = extractSkillCards(sidebar.items);

  return (
    <div className="skills-grid">
      {skills.map(({title, href, metadata}) => (
        <Link
          key={href}
          className="skill-card"
          to={href}
          aria-label={metadata.ariaLabel ?? `Explore my ${title} skills`}
        >
          <span className="skill-card__tag">{metadata.tag}</span>

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
            Explore tools →
          </span>
        </Link>
      ))}
    </div>
  );
}