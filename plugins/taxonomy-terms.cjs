const fs = require('node:fs');
const path = require('node:path');
const {engines} = require('gray-matter');

const taxonomyPath = path.join(__dirname, '../taxonomy/taxonomy.yml');
const glossaryPath = path.join(__dirname, '../glossary.yml');
const tooltipTopics = new Set(['faceted navigation', 'metadata governance']);
const inlineFormatting = new Set(['emphasis', 'strong', 'delete']);

function remarkTaxonomyTerms() {
  const {dimensions} = engines.yaml.parse(fs.readFileSync(taxonomyPath, 'utf8'));
  const terms = new Map();
  for (const {label, description, governance} of Object.values(dimensions.technologies.terms)) {
    if (governance?.status !== 'active' || !description?.trim()) continue;
    const key = label.toLowerCase();
    if (!terms.has(key)) terms.set(key, {label, description, exactCase: true});
  }
  const glossary = engines.yaml.parse(fs.readFileSync(glossaryPath, 'utf8'));
  for (const {term, definition} of glossary) {
    if (tooltipTopics.has(term) && !terms.has(term)) {
      terms.set(term, {label: term, description: definition});
    }
  }

  const labels = [...terms.values()].map(term => term.label).sort((a, b) => b.length - a.length);
  const escapedLabels = labels.map(label => label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  if (!escapedLabels.length) return;
  const pattern = new RegExp(`(?<![\\p{L}\\p{N}_])(?:${escapedLabels.join('|')})(?![\\p{L}\\p{N}_])`, 'giu');

  return tree => {
    const seen = new Set();

    function annotate(node) {
      node.children = node.children.flatMap(child => {
        if (inlineFormatting.has(child.type)) annotate(child);
        if (child.type !== 'text') return [child];

        const parts = [];
        let start = 0;
        for (const match of child.value.matchAll(pattern)) {
          const [text] = match;
          const key = text.toLowerCase();
          const term = terms.get(key);
          if (!term || seen.has(key) || (term.exactCase && text !== term.label)) continue;
          seen.add(key);

          if (match.index > start) parts.push({type: 'text', value: child.value.slice(start, match.index)});
          parts.push({
            type: 'mdxJsxTextElement',
            name: 'TaxonomyTerm',
            attributes: [{type: 'mdxJsxAttribute', name: 'definition', value: term.description}],
            children: [{type: 'text', value: text}],
          });
          start = match.index + text.length;
        }
        if (!parts.length) return [child];
        if (start < child.value.length) parts.push({type: 'text', value: child.value.slice(start)});
        return parts;
      });
    }

    function visit(node) {
      if (node.type === 'paragraph') {
        annotate(node);
      } else if (node.type === 'root' || node.type === 'blockquote' || node.type === 'list' || node.type === 'listItem') {
        node.children.forEach(visit);
      }
    }
    visit(tree);
  };
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
            use: [{loader: require.resolve('./taxonomy-tooltip-dependency.cjs'), options: {taxonomyPath, glossaryPath}}],
          }],
        },
      };
    },
  };
}

module.exports = {taxonomyTooltipPreview, remarkTaxonomyTerms};
