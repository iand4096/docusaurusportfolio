
module.exports = function ragSearchPlugin(context) {
  const baseUrl = context.siteConfig.baseUrl || '/';

  return {
    name: 'governed-rag-search',

    async contentLoaded({actions}) {
      actions.addRoute({
        path: `${baseUrl.replace(/\/$/, '')}/ai-search`,
        exact: true,
        component:
          '@site/src/components/GovernedSearch/GovernedSearchPage.tsx',
      });
    },
  };
};
