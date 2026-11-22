import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {test} from 'node:test';
import {unified} from 'unified';
import parse from 'remark-parse';
import mdx from 'remark-mdx';
import gfm from 'remark-gfm';
import frontmatter from 'remark-frontmatter';
import matching from '../../plugins/taxonomy-tooltip-matching.cjs';
import {remarkTaxonomyTerms} from '../../plugins/taxonomy-terms.cjs';

const parser = unified().use(parse).use(frontmatter).use(mdx).use(gfm);
const document = 'docs/example.md';
const review = {status: 'approved', reviewer: 'fixture', reason: 'Labelled fixture', reviewed_on: '2026-11-22'};

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'tooltip-tests-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  fs.mkdirSync(path.join(root, 'taxonomy'));
  for (const file of Object.values(matching.paths)) fs.copyFileSync(file, path.join(root, file));
  const write = (key, value) => fs.writeFileSync(path.join(root, matching.paths[key]), JSON.stringify(value));
  const config = matching.load(root);
  const term = config.active.get('requests');
  const termBasis = [term.label, term.description, term.kind, term.aliases ?? [], term.governance.status];
  write('policies', {version: 1, terms: {requests: {
    mode: 'contextual', term_basis_hash: matching.fingerprint(termBasis), review,
    competing_senses: ['incoming HTTP requests'], positive_examples: [], negative_examples: [],
  }}});
  return {root, write};
}

function render(root, source) {
  const tree = parser.parse(source);
  remarkTaxonomyTerms({repositoryRoot: root})(tree, {
    value: source, path: path.join(root, document),
    fail: message => { throw new Error(message); },
    message: () => {},
  });
  const tooltips = [];
  function visit(node) {
    if (node.name === 'TaxonomyTerm' && node.type === 'mdxJsxTextElement') tooltips.push(node);
    node.children?.forEach(visit);
  }
  visit(tree);
  return tooltips;
}

test('a rejection leaves the quota available for the first approved library mention', t => {
  const {root, write} = fixture(t);
  const source = '---\ntitle: Requests\n---\n\nCafé 🚀. Requests are validated with **Pydantic**.\n\nThe **Requests** library sends calls. Requests is mentioned again.\n\n\`Requests\` [Requests](https://example.org/Requests).\n\n\`\`\`text\nRequests\n\`\`\`\n\nUse faceted navigation.\n';
  const {mentions} = matching.scan(parser.parse(source), source, matching.load(root));
  const candidates = mentions.filter(item => item.term.id === 'requests');
  assert.equal(candidates.length, 3);
  assert.match(candidates[0].context, /Pydantic/);
  assert.equal(candidates[0].range.start, Buffer.byteLength(source.slice(0, source.indexOf('Requests are'))));
  const decisions = candidates.map((item, index) => ({
    ...matching.occurrence(item), review, result: index === 0 ? 'reject' : 'accept',
  }));
  write('decisions', {version: 1, matching_contract_version: '1',
    documents: {[document]: {content_hash: matching.hash(source), decisions}}});
  const matched = render(root, source).filter(node => node.children[0].value === 'Requests');
  assert.equal(matched.length, 1);
  const tree = parser.parse(source);
  remarkTaxonomyTerms({repositoryRoot: root})(tree, {value: source, path: path.join(root, document), message: () => {}});
  assert.equal(tree.children[2].children[1].children[0].name, 'TaxonomyTerm');
  assert.deepEqual(render(root, source + '\n').map(node => node.children[0].value), ['Pydantic', 'faceted navigation']);
});

test('explicit canonical ID resolves the definition and takes precedence', t => {
  const {root} = fixture(t);
  const source = 'Requests are validated. We used <TaxonomyTerm id="requests">Requests</TaxonomyTerm>.';
  const nodes = render(root, source);
  assert.equal(nodes.length, 1);
  assert.equal(nodes[0].attributes[0].value, matching.load(root).active.get('requests').description);
  assert.throws(() => render(root, source.replace('id="requests"', 'id="unknown"')), /Invalid explicit/);
  assert.throws(() => render(root, '[<TaxonomyTerm id="requests">Requests</TaxonomyTerm>](https://example.org)'), /ineligible/);
});
