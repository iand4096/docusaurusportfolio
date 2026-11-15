import React from 'react';
import styles from './styles.module.css';

const semantics = {
  decision: {label: 'Decision', icon: 'compass', className: styles.decision},
  rationale: {label: 'Rationale', icon: 'lightbulb', className: styles.neutral},
  constraint: {label: 'Constraint', icon: 'lock', className: styles.neutral},
  'trade-off': {label: 'Trade-off', icon: 'scale-balanced', className: styles.neutral},
  risk: {label: 'Risk', icon: 'triangle-exclamation', className: styles.risk},
  outcome: {label: 'Outcome', icon: 'circle-check', className: styles.outcome},
  contribution: {label: 'Contribution', icon: 'pen-to-square', className: styles.neutral},
  validation: {label: 'Validation', icon: 'clipboard-check', className: styles.neutral},
};

const appearances = {
  inline: styles.inline,
  row: styles.row,
  accent: styles.accent,
};

export function SemanticLabelGroup({children}) {
  return <div className={styles.group}>{children}</div>;
}

export default function SemanticLabel({
  type = 'decision',
  appearance = 'inline',
  children,
}) {
  const semantic = typeof type === 'string' && Object.hasOwn(semantics, type)
    ? semantics[type]
    : semantics.decision;
  const presentation = typeof appearance === 'string' && Object.hasOwn(appearances, appearance)
    ? appearance
    : 'inline';

  return (
    <div className={`${styles.root} ${semantic.className} ${appearances[presentation]}`}>
      <strong className={styles.label}>
        {presentation !== 'inline' && (
          <i className={`fa-solid fa-${semantic.icon} ${styles.icon}`} aria-hidden="true" />
        )}
        {semantic.label}{presentation === 'inline' ? ':' : null}
      </strong>{' '}
      <div className={styles.content}>{children}</div>
    </div>
  );
}
