type MetadataFilters = Partial<Record<string, string[]>>;

/** Match the API's metadata rules against catalogue documents, not passages. */
export function documentInSearchScope(
  document: Record<string, unknown>,
  included: MetadataFilters,
  excluded: MetadataFilters,
  includeArchived: boolean,
): boolean {
  const values = (field: string): string[] =>
    Array.isArray(document[field]) ? document[field] as string[] : [];
  if (Object.entries(excluded).some(([field, terms]) =>
    terms?.some(term => values(field).includes(term)))) return false;
  if (!includeArchived && !(included.lifecycle ?? []).includes('archived') &&
      values('lifecycle').includes('archived')) return false;
  return Object.entries(included).every(([field, terms]) =>
    !terms?.length || terms.some(term => values(field).includes(term)));
}
