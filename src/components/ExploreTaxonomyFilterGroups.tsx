import React from 'react';
import navigationIndex from '@site/src/generated/taxonomy-navigation.json';
import browseStyles from '@site/src/pages/browse/styles.module.css';

import {filterDimensions, valuesForDimension, type TaxonomyTerm as NavigationTerm,
  type TaxonomyDimension as NavigationDimension} from '@site/src/utils/taxonomyFilters';

/** One filter UI and catalogue-count source for Browse and AI Search. */
export type ExploreDimensionId = string;

type TechnologyKind = {label: string; description?: string};
type NavigationCatalogue = {
  dimensions: Record<ExploreDimensionId, NavigationDimension>;
  technologyKinds?: Record<string, TechnologyKind>;
  documents: Array<Record<string, unknown>>;
};

const catalogue = navigationIndex as NavigationCatalogue;
const DIMENSIONS = filterDimensions(catalogue.dimensions);

// These are catalogue document counts, not AI passage counts. Compute once from
// the same generated index that powers Browse; both tabs display identical values.
const DOCUMENT_COUNTS: Record<ExploreDimensionId, Record<string, number>> =
  Object.fromEntries(DIMENSIONS.map(dimension => {
    const dimensionId = dimension.id;
    const counts = Object.fromEntries(dimension.terms.map(term => [
      term.id,
      catalogue.documents.reduce((count, document) => {
        return count + Number(valuesForDimension(document, dimension).includes(term.id));
      }, 0),
    ]));
    return [dimensionId, counts];
  })) as Record<ExploreDimensionId, Record<string, number>>;

// Keep the browser's native <details> behaviour (including manual collapse),
// but open a group if selections arrive later from a restored search session.
function TechnologyFilterGroup({
  label, description, terms, hasSelected, renderChip,
}: {
  label: string;
  description?: string;
  terms: NavigationTerm[];
  hasSelected: boolean;
  renderChip: (term: NavigationTerm) => React.JSX.Element;
}): React.JSX.Element {
  const detailsRef = React.useRef<HTMLDetailsElement>(null);
  React.useEffect(() => {
    if (hasSelected && detailsRef.current) detailsRef.current.open = true;
  }, [hasSelected]);
  return (
    <details ref={detailsRef} title={description}
      style={{width: '100%', flexBasis: '100%', marginTop: '0.35rem'}}>
      <summary style={{cursor: 'pointer', fontWeight: 600}}>
        {label} ({terms.length})
      </summary>
      <div className={browseStyles.filterOptions}>
        {[...terms].sort((a, b) => a.label.localeCompare(b.label)).map(renderChip)}
      </div>
    </details>
  );
}

export function ExploreTaxonomyFilterGroups({
  isSelected, onToggle, disabled = false,
}: {
  isSelected: (dimensionId: ExploreDimensionId, termId: string) => boolean;
  onToggle: (dimensionId: ExploreDimensionId, termId: string) => void;
  disabled?: boolean;
}): React.JSX.Element {
  function renderChip(dimensionId: ExploreDimensionId, term: NavigationTerm): React.JSX.Element {
    const selected = isSelected(dimensionId, term.id);
    return (
      <button key={term.id} type="button"
        className={`${browseStyles.filterChip} ${selected ? browseStyles.filterChipSelected : ''}`}
        aria-pressed={selected} disabled={disabled}
        title={term.description}
        onClick={() => onToggle(dimensionId, term.id)}>
        <span>{term.label}</span>
        <span className={browseStyles.count}>{DOCUMENT_COUNTS[dimensionId][term.id] ?? 0}</span>
      </button>
    );
  }

  return (
    <>
      {DIMENSIONS.map(dimension => {
        const dimensionId = dimension.id;

        let options: React.JSX.Element;
        if (dimensionId === 'technologies' && catalogue.technologyKinds) {
          // Use the same kind groups in both tabs. The original Browse view
          // already groups technologies; AI Search now follows that convention.
          const groups = new Map<string, NavigationTerm[]>();
          for (const term of dimension.terms) {
            const kindId = term.kind ?? 'other';
            groups.set(kindId, [...(groups.get(kindId) ?? []), term]);
          }
          const orderedGroups = [...groups.entries()].sort(([a], [b]) =>
            (catalogue.technologyKinds?.[a]?.label ?? a).localeCompare(
              catalogue.technologyKinds?.[b]?.label ?? b));
          options = (
            <div className={browseStyles.filterOptions}>
              {orderedGroups.map(([kindId, terms]) => {
                const kind = catalogue.technologyKinds?.[kindId];
                return (
                  <TechnologyFilterGroup key={kindId}
                    label={kind?.label ?? (kindId === 'other' ? 'Other' : kindId)}
                    description={kind?.description} terms={terms}
                    hasSelected={terms.some(term => isSelected(dimensionId, term.id))}
                    renderChip={term => renderChip(dimensionId, term)}
                  />
                );
              })}
            </div>
          );
        } else {
          options = (
            <div className={browseStyles.filterOptions}>
              {dimension.terms.map(term => renderChip(dimensionId, term))}
            </div>
          );
        }
        return (
          <section className={browseStyles.filterGroup} key={dimensionId} aria-label={`${dimension.label} filters`}>
            <h3 className={browseStyles.filterLabel}>{dimension.label}</h3>
            {options}
          </section>
        );
      })}
    </>
  );
}
