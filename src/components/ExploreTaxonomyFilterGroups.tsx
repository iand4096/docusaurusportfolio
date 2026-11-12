import React from 'react';
import navigationIndex from '@site/src/generated/taxonomy-navigation.json';
import browseStyles from '@site/src/pages/browse/styles.module.css';

/** One filter UI and catalogue-count source for Browse and AI Search. */
export type ExploreDimensionId =
  | 'content_types'
  | 'topics'
  | 'technologies'
  | 'audiences'
  | 'lifecycle';

type NavigationTerm = {
  id: string;
  label: string;
  description?: string;
  kind?: string;
};
type NavigationDimension = {
  id: ExploreDimensionId;
  label: string;
  metadataField: string;
  multiple: boolean;
  terms: NavigationTerm[];
};
type TechnologyKind = {label: string; description?: string};
type NavigationCatalogue = {
  dimensions: Record<ExploreDimensionId, NavigationDimension>;
  technologyKinds?: Record<string, TechnologyKind>;
  documents: Array<Record<string, unknown>>;
};

const catalogue = navigationIndex as NavigationCatalogue;
const DIMENSION_ORDER: ExploreDimensionId[] = [
  'content_types', 'topics', 'technologies', 'audiences', 'lifecycle',
];

// These are catalogue document counts, not AI passage counts. Compute once from
// the same generated index that powers Browse; both tabs display identical values.
const DOCUMENT_COUNTS: Record<ExploreDimensionId, Record<string, number>> =
  Object.fromEntries(DIMENSION_ORDER.map(dimensionId => {
    const dimension = catalogue.dimensions[dimensionId];
    const counts = Object.fromEntries(dimension.terms.map(term => [
      term.id,
      catalogue.documents.reduce((count, document) => {
        const values = document[dimension.metadataField];
        return count + Number(Array.isArray(values) && values.includes(term.id));
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
  isSelected, onToggle, isExcluded, onExcludeToggle, disabled = false,
}: {
  isSelected: (dimensionId: ExploreDimensionId, termId: string) => boolean;
  onToggle: (dimensionId: ExploreDimensionId, termId: string) => void;
  isExcluded?: (dimensionId: ExploreDimensionId, termId: string) => boolean;
  onExcludeToggle?: (dimensionId: ExploreDimensionId, termId: string) => void;
  disabled?: boolean;
}): React.JSX.Element {
  const helpId = React.useId();
  const [modes, setModes] = React.useState<Record<string, string>>({});
  function modeFor(dimensionId: ExploreDimensionId): string {
    const dimension = catalogue.dimensions[dimensionId];
    if (!dimension.multiple) {
      if (dimension.terms.some(term => isSelected(dimensionId, term.id))) return 'include';
      if (dimension.terms.some(term => isExcluded?.(dimensionId, term.id))) return 'exclude';
    }
    return modes[dimensionId] ?? 'include';
  }

  function changeMode(dimensionId: ExploreDimensionId, mode: string): void {
    setModes(current => ({...current, [dimensionId]: mode}));
    if (!catalogue.dimensions[dimensionId].multiple) {
      for (const term of catalogue.dimensions[dimensionId].terms) {
        if (mode === 'exclude' && isSelected(dimensionId, term.id)) onExcludeToggle?.(dimensionId, term.id);
        if (mode === 'include' && isExcluded?.(dimensionId, term.id)) onToggle(dimensionId, term.id);
      }
    }
  }

  function renderChip(dimensionId: ExploreDimensionId, term: NavigationTerm): React.JSX.Element {
    const selected = isSelected(dimensionId, term.id);
    const excluded = isExcluded?.(dimensionId, term.id) ?? false;
    return (
      <button key={term.id} type="button"
        className={`${browseStyles.filterChip} ${selected ? (onExcludeToggle ? browseStyles.filterInclude : browseStyles.filterChipSelected) : excluded ? browseStyles.filterExclude : ''}`}
        aria-pressed={selected || excluded} disabled={disabled}
        title={term.description}
        onClick={() => modeFor(dimensionId) === 'exclude' && onExcludeToggle ? onExcludeToggle(dimensionId, term.id) : onToggle(dimensionId, term.id)}>
        <span>{selected && onExcludeToggle ? '+ ' : excluded ? '− ' : ''}{term.label}</span>
        <span className={browseStyles.count}>{DOCUMENT_COUNTS[dimensionId][term.id] ?? 0}</span>
      </button>
    );
  }

  return (
    <>
      {DIMENSION_ORDER.map(dimensionId => {
        const dimension = catalogue.dimensions[dimensionId];
        if (!dimension || dimension.terms.length === 0) return null;

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
                    hasSelected={terms.some(term => isSelected(dimensionId, term.id) || isExcluded?.(dimensionId, term.id))}
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
            {onExcludeToggle && <>
              <div className={browseStyles.filterMode} role="group" aria-label={`${dimension.label} selection mode`}>
                {['include', 'exclude'].map(mode => <button type="button" key={mode} disabled={disabled}
                  aria-pressed={modeFor(dimensionId) === mode}
                  className={modeFor(dimensionId) === mode ? (mode === 'include' ? browseStyles.filterInclude : browseStyles.filterExclude) : ''}
                  aria-describedby={`${helpId}-${dimensionId}`}
                  onClick={() => changeMode(dimensionId, mode)}>
                  {mode === 'include' ? '+ Include' : '− Exclude'}
                </button>)}
              </div>
              <p id={`${helpId}-${dimensionId}`} className={browseStyles.filterModeHint}>
                {dimension.multiple ? 'Applies to your next selection.' : 'Applies to all selected tags.'}
              </p>
            </>}
            {options}
          </section>
        );
      })}
    </>
  );
}
