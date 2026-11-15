const fs = require('node:fs/promises');
const path = require('node:path');

module.exports = function taxonomyCoveragePlugin({siteDir}) {
  const cataloguePath = path.join(siteDir, 'src/generated/taxonomy-navigation.json');
  return {
    name: 'taxonomy-coverage',
    getPathsToWatch() { return [cataloguePath]; },
    async loadContent() {
      const catalogue = JSON.parse(await fs.readFile(cataloguePath, 'utf8'));
      for (const dimension of Object.values(catalogue.dimensions)) {
        const used = new Set(catalogue.documents.flatMap(document => {
          const values = document[dimension.metadataField];
          return Array.isArray(values) ? values : [];
        }));
        for (const term of dimension.terms) {
          if (!used.has(term.id)) {
            console.warn(`[WARNING] [taxonomy-coverage] ${dimension.id}.${term.id} (${term.label}): ` +
              '0 catalogue documents; hidden from Explore filters. Review document metadata or retire the unused term.');
          }
        }
      }
      return null;
    },
  };
};
