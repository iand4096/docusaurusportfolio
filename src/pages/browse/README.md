# Browse knowledge: relevance-ranked local search

The reusable browse interface, its `DocumentTags` helper, search-ranking helpers and styles live in [`src/components/BrowseExperience`](../../components/BrowseExperience/index.tsx).

The [Explore page](../explore/index.tsx) imports `BrowseExperience` and embeds it in its Browse tab. This directory contains only the legacy `/browse` route redirect, which preserves query parameters and the hash while selecting the Browse tab on `/explore`.

## Local verification

Run `npm run build`, then `npm run start -- --no-open`. Visit `/docusaurusportfolio/explore?view=browse` to use the interface, or `/docusaurusportfolio/browse` to check the redirect.

## What changed {/* #what-changed */}

- Live, client-side relevance ranking. Title matches score more heavily than descriptions, which score above taxonomy and path matches.
- Case/punctuation/diacritic normalisation: `docs-as-code` and `docs as code` behave alike.
- Token-based multi-word search: words can occur in different metadata fields and in any order. Every search term must match.
- Prefix matching and conservative one-edit typo tolerance for words with five or more characters.
- Relevance order when searching, alphabetical order when the query is blank.
- Compact “matched in” and relevance-sort indicators, plus help text and clearer zero-result messaging.
- Existing taxonomy dimensions, chip selections, facet counts, URL `contentType` query handling, document links and mobile layout are preserved.

## Important boundaries {/* #important-boundaries */}

This searches the fields available in `src/generated/taxonomy-navigation.json`: title, description, taxonomy labels, and path. **It does not search Markdown/MDX document bodies**, which are absent from that generated data. For full-document text search, enhance the build-time index generator and rework result links to include heading anchors.

This is dependency-free: no npm package, Azure changes, Docker rebuild, or external search service is needed.

## Quick tests {/* #quick-tests */}

- Query a phrase with a title match: title-matching entries should rank before weaker metadata matches.
- Test a typo in a word with >=5 characters and test multiple words in a different order.
- Test `docs-as-code` against `docs as code`.
- Select taxonomy chips: results must still obey `OR` within each category and `AND` across categories.
- Clear all: restores the alphabetical list.
- Check desktop and mobile, light and dark themes.

## Metadata filter visibility

Browse and Search share a show/hide control for metadata filters at every viewport
width. The options start hidden; search stays visible. The eye icon and text label
indicate the action, and `aria-expanded` exposes the current state. Hidden options
are excluded from keyboard navigation.

Visibility is stored as `metadata-filters-visible` in browser local storage and
synchronizes between the Explore tabs and browser tabs. This preference is separate
from Search’s tab-local saved results. Clearing a search does not change it. If
storage is blocked, the toggle continues to work for the current session. Hiding
options does not clear selected filters; the toggle retains their selected count.
