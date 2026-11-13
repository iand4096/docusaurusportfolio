const path = require('node:path');
const {pathToFileURL} = require('node:url');

module.exports = function seeAlsoPlugin({siteDir, siteConfig}) {
  const implementation = import(pathToFileURL(path.join(siteDir, 'scripts/lib/see-also.mjs')).href);
  return {
    name: 'see-also',
    loadContent() { return null; },
    getPathsToWatch() {
      // The official docs plugin watches articles. Its reload also re-runs every
      // allContentLoaded hook, with up-to-date permalinks. Watch only the extra
      // catalogue input here to avoid racing a second reload of the same file.
      return [path.join(siteDir, 'src/generated/taxonomy-navigation.json')];
    },
    async allContentLoaded({allContent, actions}) {
      const {generate, writeArtifacts} = await implementation;
      const content = allContent['docusaurus-plugin-content-docs']?.default;
      const docs = (content?.loadedVersions ?? []).flatMap(version => [...version.docs, ...version.drafts]);
      const result = await generate(siteDir, siteConfig, docs);
      await writeArtifacts(siteDir, result);
      const base = (siteConfig.baseUrl || '/').replace(/\/$/, '');
      actions.setGlobalData({byPath: Object.fromEntries(Object.values(result.index.pages)
        .map(page => [`${base}${page.path}`, page.links]))});
    },
  };
};
