const path = require('node:path');
const matcher = require('./taxonomy-tooltip-matching.cjs');

const root = path.resolve(__dirname, '..');

function remarkTaxonomyTerms({repositoryRoot = root} = {}) {
  return (tree, file) => {
    const config = matcher.load(repositoryRoot);
    const source = String(file.value);
    const document = path.relative(repositoryRoot, file.path).split(path.sep).join('/');
    const {mentions, explicit, errors} = matcher.scan(
      tree, source, config, file.data?.frontMatter?.taxonomy_tooltip_exclude);
    if (errors.length) file.fail(errors.join('\n'));
    const decisions = matcher.indexDecisions(config.manifest, document, source);
    const seen = new Set();
    const selected = new Map();
    const held = term => term.mode === 'contextual' && config.holds.has(term.id);

    for (const {child, term} of explicit) {
      if (seen.has(term.id) || held(term)) {
        Object.assign(child, {type: 'text', value: child.children[0].value});
      } else {
        seen.add(term.id);
        child.attributes = definition(term);
      }
    }

    for (const mention of mentions) {
      const {term, child} = mention;
      if (['off', 'explicit'].includes(term.mode) || held(term)) continue;
      if (term.mode === 'contextual') {
        const decision = matcher.reviewedDecision(decisions, mention);
        if (!decision) file.message('Contextual tooltip needs review for ' + term.id, child);
        if (decision?.result !== 'accept') continue;
      }
      if (seen.has(term.id)) continue;
      seen.add(term.id);
      if (!selected.has(child)) selected.set(child, []);
      selected.get(child).push(mention);
    }

    function rewrite(node) {
      if (!node.children) return;
      node.children = node.children.flatMap(child => {
        const matches = selected.get(child);
        if (!matches) {
          rewrite(child);
          return [child];
        }
        const parts = [];
        let start = 0;
        for (const {index, text, term} of matches) {
          if (index > start) parts.push({type: 'text', value: child.value.slice(start, index)});
          parts.push({type: 'mdxJsxTextElement', name: 'TaxonomyTerm',
            attributes: definition(term), children: [{type: 'text', value: text}]});
          start = index + text.length;
        }
        if (start < child.value.length) parts.push({type: 'text', value: child.value.slice(start)});
        return parts;
      });
    }
    rewrite(tree);
  };
}

function definition(term) {
  return [{type: 'mdxJsxAttribute', name: 'definition', value: term.description}];
}

/** @returns {import('@docusaurus/types').Plugin} */
function taxonomyTooltipPreview({siteDir}) {
  return {
    name: 'taxonomy-tooltip-preview',
    configureWebpack() {
      return {
        module: {
          rules: [{
            test: /\.mdx?$/,
            include: path.join(siteDir, 'docs') + path.sep,
            enforce: 'pre',
            use: [{loader: require.resolve('./taxonomy-tooltip-dependency.cjs'), options: {dependencies: Object.values(matcher.paths).map(file => path.join(root, file))}}],
          }],
        },
      };
    },
  };
}

module.exports = {taxonomyTooltipPreview, remarkTaxonomyTerms};
