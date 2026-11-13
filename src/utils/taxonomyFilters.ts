/** Filter behaviour shared by Browse and Search; dimensions come from generated data. */
export type TaxonomyTerm = {id: string; label: string; description?: string; kind?: string; parent?: string};
export type TaxonomyDimension = {id: string; label: string; metadataField: string; terms: TaxonomyTerm[]};
export type TaxonomyDimensions = Record<string, TaxonomyDimension>;
export type SelectedFilters = Record<string, Set<string>>;
export type SelectedFacets = Partial<Record<string, string[]>>;

export function filterDimensions(dimensions: TaxonomyDimensions): TaxonomyDimension[] {
  return Object.values(dimensions).filter(dimension => dimension.terms.length > 0);
}

export function emptyFilters(dimensions: TaxonomyDimensions): SelectedFilters {
  return Object.fromEntries(filterDimensions(dimensions).map(({id}) => [id, new Set<string>()]));
}

export function valuesForDimension(document: Record<string, unknown>, dimension: TaxonomyDimension): string[] {
  const values = document[dimension.metadataField];
  return Array.isArray(values) ? values.filter((value): value is string => typeof value === 'string') : [];
}

export function documentMatchesFilters(
  document: Record<string, unknown>, selected: SelectedFilters, dimensions: TaxonomyDimensions,
): boolean {
  return filterDimensions(dimensions).every(dimension => {
    const terms = selected[dimension.id];
    return !terms?.size || valuesForDimension(document, dimension).some(term => terms.has(term));
  });
}

export function filtersFromParams(params: URLSearchParams, dimensions: TaxonomyDimensions): SelectedFilters {
  const selected = emptyFilters(dimensions);
  for (const dimension of filterDimensions(dimensions)) {
    const names = new Set([dimension.id, dimension.metadataField]);
    if (dimension.metadataField === 'type') names.add('contentType'); // Existing homepage links.
    const valid = new Set(dimension.terms.map(term => term.id));
    for (const name of names) {
      for (const value of params.getAll(name)) {
        if (valid.has(value)) selected[dimension.id].add(value);
      }
    }
  }
  return selected;
}

export function restoreFacets(saved: Record<string, unknown>, dimensions: TaxonomyDimensions): SelectedFacets {
  const facets: SelectedFacets = {};
  for (const dimension of filterDimensions(dimensions)) {
    const raw = saved[dimension.metadataField];
    const values = Array.isArray(raw) ? raw : typeof raw === 'string' ? [raw] : [];
    const valid = new Set(dimension.terms.map(term => term.id));
    const selected = [...new Set(values.filter((value): value is string => typeof value === 'string' && valid.has(value)))];
    if (selected.length) facets[dimension.metadataField] = selected;
  }
  return facets;
}

export function facetDefinitions(dimensions: TaxonomyDimensions): {key: string; label: string}[] {
  return filterDimensions(dimensions).map(({metadataField, label}) => ({key: metadataField, label}));
}
