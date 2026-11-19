const fs = require('node:fs');
const path = require('node:path');
const {engines} = require('gray-matter');

const cataloguePath = path.join(__dirname, '../src/generated/taxonomy-navigation.json');
const glossaryPath = path.join(__dirname, '../glossary.yml');
const proseDimensions = ['topics', 'technologies', 'organisations'];
const inlineFormatting = new Set(['emphasis', 'strong', 'delete']);

function addGlossaryTerms(terms) {
  const entries = engines.yaml.parse(fs.readFileSync(glossaryPath, 'utf8'));
  if (!Array.isArray(entries)) throw new Error('glossary.yml must contain a list of entries.');

  const isNonEmptyString = value => typeof value === 'string' && value.trim().length > 0;
  for (const [index, entry] of entries.entries()) {
    const {term, definition, aliases = []} = entry ?? {};
    if (!isNonEmptyString(term) || !isNonEmptyString(definition) ||
        !Array.isArray(aliases) || !aliases.every(isNonEmptyString)) {
      throw new Error(`glossary.yml entry ${index + 1} needs a term, a definition and an optional list of aliases.`);
    }

    const id = term.trim().toLowerCase();
    for (const name of [term, ...aliases]) {
      const label = name.trim();
      const key = label.toLowerCase();
      if (terms.has(key)) {
        throw new Error(`glossary.yml entry ${index + 1} repeats an existing glossary or taxonomy term: ${label}`);
      }
      terms.set(key, {id, label, description: definition.trim()});
    }
  }
}

function remarkTaxonomyTerms() {
  const {dimensions} = JSON.parse(fs.readFileSync(cataloguePath, 'utf8'));
  const terms = new Map();
  for (const dimension of proseDimensions) {
    for (const {label, description} of dimensions[dimension].terms) {
      if (!description?.trim()) continue;
      const key = label.toLowerCase();
      if (!terms.has(key)) {
        terms.set(key, {id: key, label, description, exactCase: dimension !== 'topics'});
      }
    }
  }
  addGlossaryTerms(terms);

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
          if (!term || seen.has(term.id) || (term.exactCase && text !== term.label)) continue;
          seen.add(term.id);

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
function glossaryPreview({siteDir}) {
  return {
    name: 'glossary-preview',
    configureWebpack() {
      return {
        module: {
          rules: [{
            test: /\.mdx?$/,
            include: path.join(siteDir, 'docs') + path.sep,
            enforce: 'pre',
            use: [{loader: require.resolve('./glossary-dependency.cjs'), options: {glossaryPath}}],
          }],
        },
      };
    },
  };
}

module.exports = {glossaryPreview, remarkTaxonomyTerms};
