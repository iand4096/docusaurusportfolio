const path = require('node:path');
const {parseReference, serializeSourceSnippets} = require('./source-snippets.cjs');

module.exports = function trackSourceSnippetDependencies(content) {
  serializeSourceSnippets(content, meta => {
    const {relative} = parseReference(meta);
    this.addDependency(path.join(this.rootContext, relative));
    return {code: ''};
  });
  return content;
};
