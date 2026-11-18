/** Keep Scalar's already-built standalone browser script intact. */
module.exports = function scalarBrowser() {
  return {
    name: 'scalar-browser',
    configureWebpack() {
      return {
        plugins: [{
          apply(compiler) {
            compiler.hooks.thisCompilation.tap('ScalarBrowser', compilation => {
              compilation.hooks.processAssets.tap({
                name: 'ScalarBrowser',
                stage: compiler.webpack.Compilation.PROCESS_ASSETS_STAGE_PRE_PROCESS,
              }, () => {
                for (const {name, info} of compilation.getAssets()) {
                  if (!info.sourceFilename?.endsWith('@scalar/api-reference/dist/browser/standalone.js')) continue;
                  compilation.updateAsset(name, source => source, {...info, minimized: true});
                }
              });
            });
          },
        }],
      };
    },
  };
};
