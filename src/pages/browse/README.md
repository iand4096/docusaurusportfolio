# Browse knowledge: relevance-ranked local search

These are replacement files for the existing Docusaurus Browse page (not the Azure AI Search page).

## Install {/* #install */}

1. Back up the existing files in `src/pages/browse/`.
2. Copy `index.tsx` and `styles.module.css` from this package into `src/pages/browse/`.
3. Run `npm run build`, then `npm run start` and open `/docusaurusportfolio/browse`.

## What changed {/* #what-changed */}

- Live, client-side relevance ranking. Title matches score more heavily than descriptions, which score above taxonomy and path matches.
- Case/punctuation/diacritic normalization: `docs-as-code` and `docs as code` behave alike.
- Token-based multiword search: words can occur in different metadata fields and in any order. Every search term must match.
- Prefix matching and conservative one-edit typo tolerance for words with five or more characters.
- Relevance order when searching, alphabetical order when the query is blank.
- Compact “matched in” and relevance-sort indicators, plus help text and clearer zero-result messaging.
- Existing taxonomy dimensions, chip selections, facet counts, URL contentType query handling, document links, and mobile layout preserved.

## Important boundaries {/* #important-boundaries */}

This searches the fields available in `src/generated/taxonomy-navigation.json`: title, description, taxonomy labels, and path. **It does not search Markdown/MDX document bodies**, which are absent from that generated data. For full-document text search, enhance the build-time index generator and rework result links to include heading anchors.

This is dependency-free: no npm package, Azure changes, Docker rebuild, or external search service is needed.

## Quick tests {/* #quick-tests */}

- Query a phrase with a title match: title-matching entries should rank before weaker metadata matches.
- Test a typo in a word with >=5 characters and test multiple words in a different order.
- Test `docs-as-code` against `docs as code`.
- Select taxonomy chips: results must still obey OR within each category and AND across categories.
- Clear all: restores the alphabetic list.
- Check desktop and mobile, light and dark themes.
