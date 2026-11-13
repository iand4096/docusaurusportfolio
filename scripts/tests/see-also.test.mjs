import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {createResolver, eligibility, extractLinks, generate, rankCandidates, SETTINGS,
  validateOptions, writeArtifacts} from '../lib/see-also.mjs';

const config = {url: 'https://example.com', baseUrl: '/portfolio/', plugins: [
  ['@docusaurus/plugin-client-redirects', {redirects: [{from: '/docs/old', to: '/docs/target'}]}],
]};
const dimensions = Object.fromEntries(['topics', 'technologies', 'audiences', 'organisations'].map(id => [id, {
  id, label: id, metadataField: id,
  terms: ['focused', 'other', 'rare', 'common', 'team'].map(value => ({id: value, label: value})),
}]));
function doc(id, fields = {}, body = '') {
  return {id, source: `docs/${id}.md`, title: id, path: `/docs/${id}`,
    frontMatter: {type: ['case-study'], lifecycle: ['current'], topics: [], technologies: [], ...fields}, body};
}
function corpus() {
  return [doc('source', {topics: ['focused']}), doc('target', {topics: ['focused']}),
    doc('other', {topics: ['other']}), doc('fourth', {topics: ['rare']})];
}

test('eligibility excludes overviews, drafts, unlisted and archived pages but keeps historical samples', () => {
  for (const fields of [{type: ['landing-page']}, {draft: true}, {unlisted: true}, {lifecycle: ['archived']}]) {
    assert.ok(eligibility(doc('page', fields)));
  }
  assert.equal(eligibility(doc('page', {lifecycle: ['historical']})), null);
});

test('syntax extraction handles reference links, autolinks, literal JSX and ignores code, images and comments', () => {
  const body = '[First](./target.md) and [second][ref].\n\n[ref]: /docs/other\n\n' +
    '<https://example.com/portfolio/docs/target>\n\n' +
    '<Link to="/docs/fourth">Go</Link>\n\n<a href={"/docs/target#section"}>Go</a>\n\n' +
    '![Image](./image.md)\n\n`[Code](./code.md)`\n\n```md\n[Example](./example.md)\n```\n\n' +
    '<!-- [Hidden](./hidden.md) -->\n\n{/* [Hidden](./hidden-mdx.md) */}';
  const parsed = extractLinks(body, 'source.md');
  assert.deepEqual(parsed.links.map(link => link.url), ['./target.md', '/docs/other',
    'https://example.com/portfolio/docs/target', '/docs/fourth', '/docs/target#section']);
  assert.equal(parsed.warnings.length, 0);
});

test('dynamic MDX links are reported, never guessed', () => {
  const parsed = extractLinks('<Link to={destination}>Go</Link>', 'source.mdx');
  assert.equal(parsed.links.length, 0);
  assert.match(parsed.warnings[0].reason, /Dynamic to/);
});

test('route resolution normalises file links, anchors, base URLs, encoded paths and redirects', () => {
  const documents = corpus();
  const resolve = createResolver(documents, config);
  for (const url of ['./target.md#heading', '/docs/target?query=x', '/portfolio/docs/target/',
    'https://example.com/portfolio/docs/target#heading', '/docs/old', './targ%65t.md',
    'pathname:///docs/target', '@site/docs/target.md']) {
    assert.equal(resolve(url, documents[0]).id, 'target', url);
  }
  assert.deepEqual(resolve('https://elsewhere.example/docs/target', documents[0]), {});
  assert.deepEqual(resolve('#section', documents[0]), {});
  assert.deepEqual(resolve('../tags.yml', documents[0]), {});
  assert.match(resolve('./missing.md', documents[0]).warning, /Unresolved/);
});

test('body links suppress a destination once even when multiple sections or URL forms are linked', () => {
  const documents = corpus();
  documents[0].body = '[One](./target.md#a) [Two](/docs/target#b)';
  const result = rankCandidates(documents, dimensions, config);
  assert.equal(result.pages.source.links.length, 0);
  assert.deepEqual(result.review.find(page => page.id === 'source').excluded
    .filter(item => item.id === 'target'), [{id: 'target', reason: 'already linked in article body'}]);
});

test('same-employer body links remain eligible but manual exclusions still apply', () => {
  const documents = corpus();
  documents[0].frontMatter.organisations = ['team'];
  documents[1].frontMatter.organisations = ['team'];
  documents[0].body = '[Target](./target.md#section)';
  assert.equal(rankCandidates(documents, dimensions, config).pages.source.links[0].id, 'target');
  documents[0].frontMatter.see_also = {exclude: ['target']};
  assert.equal(rankCandidates(documents, dimensions, config).pages.source.links.length, 0);
});

test('manual exclusions are validated and another qualifying candidate fills the slot', () => {
  const documents = corpus();
  documents.push(doc('replacement', {topics: ['focused']}));
  documents[0].frontMatter.see_also = {exclude: ['target']};
  const result = rankCandidates(documents, dimensions, config);
  assert.deepEqual(result.pages.source.links.map(link => link.id), ['replacement']);
  documents[0].frontMatter.see_also.exclude = ['typo'];
  assert.throws(() => rankCandidates(documents, dimensions, config), /existing document IDs/);
});

test('disabled pages have no outgoing recommendations but remain eligible destinations', () => {
  const documents = corpus();
  documents[1].frontMatter.see_also = {enabled: false};
  const result = rankCandidates(documents, dimensions, config);
  assert.equal(result.pages.target.links.length, 0);
  assert.equal(result.pages.source.links[0].id, 'target');
});

test('audience, employer, type and ubiquitous subject terms alone cannot create recommendations', () => {
  const documents = corpus().map(document => ({...document, frontMatter: {...document.frontMatter,
    topics: ['common'], audiences: ['team'], organisations: ['team']}}));
  const result = rankCandidates(documents, dimensions, config);
  assert.ok(Object.values(result.pages).every(page => !page.links.length));
});

test('extra destination topics do not dilute source coverage and ties use document IDs', () => {
  const documents = corpus();
  documents.push(doc('broad', {topics: ['focused', 'other', 'rare'], technologies: ['extra']}));
  documents.push(doc('another', {topics: ['focused']}));
  documents.push(doc('seventh', {topics: ['unrelated']}));
  const result = rankCandidates(documents, dimensions, config);
  assert.deepEqual(result.pages.source.links.map(link => link.id), ['another', 'broad', 'target']);
  assert.equal(result.pages.source.links[0].score, result.pages.source.links[1].score);
  assert.equal(result.pages.source.links[1].score, result.pages.source.links[2].score);
  assert.ok(result.pages.source.links.length <= SETTINGS.limit);
  assert.deepEqual(rankCandidates(documents.toReversed(), dimensions, config).pages.source.links,
    result.pages.source.links);
});

test('shared employer raises a related page above a closer subject-only match', () => {
  const documents = [
    doc('source', {topics: ['focused', 'other'], organisations: ['team']}),
    doc('subject-match', {topics: ['focused', 'other']}),
    doc('employer-match', {topics: ['focused'], organisations: ['team']}),
    doc('unrelated-employer', {topics: ['rare'], organisations: ['team']}),
    doc('unrelated', {topics: ['rare']}),
  ];
  const result = rankCandidates(documents, dimensions, config);
  assert.equal(result.pages.source.links[0].id, 'employer-match');
  assert.ok(result.pages.source.links.some(link => link.id === 'subject-match'));
  assert.ok(!result.pages.source.links.some(link => link.id === 'unrelated-employer'));
});

test('broad topics cannot establish relevance or affect scores and explanations', () => {
  const documents = corpus();
  documents.push(doc('broad-only', {topics: [...SETTINGS.ignoredTopics], organisations: ['team']}));
  documents[0].frontMatter.organisations = ['team'];
  const before = rankCandidates(documents, dimensions, config).pages.source.links;
  documents[0].frontMatter.topics.push(...SETTINGS.ignoredTopics);
  documents[1].frontMatter.topics.push(...SETTINGS.ignoredTopics);
  const after = rankCandidates(documents, dimensions, config).pages.source.links;
  assert.deepEqual(after, before);
  assert.ok(!after.some(link => link.id === 'broad-only'));
  assert.ok(after.every(link => link.reasons.every(reason =>
    !SETTINGS.ignoredTopics.some(term => reason.includes(`(${term})`)))));
});

test('additional destination technologies do not dilute a technology match', () => {
  const documents = corpus();
  documents[0].frontMatter.technologies = ['focused'];
  documents[1].frontMatter.technologies = ['focused'];
  const before = rankCandidates(documents, dimensions, config).pages.source.links[0];
  documents[1].frontMatter.technologies.push('extra', 'other', 'rare');
  const after = rankCandidates(documents, dimensions, config).pages.source.links[0];
  assert.equal(after.id, before.id);
  assert.equal(after.score, before.score);
});

test('rare technologies outweigh common technology and topic-only matches', () => {
  const documents = [
    doc('source', {topics: ['focused'], technologies: ['rare', 'common']}),
    doc('rare-match', {technologies: ['rare']}),
    doc('common-match', {technologies: ['common']}),
    doc('topic-match', {topics: ['focused']}),
    ...Array.from({length: 6}, (_, i) => doc(`filler-${i}`, {technologies: ['common']})),
  ];
  const result = rankCandidates(documents, dimensions, config);
  assert.equal(result.pages.source.links[0].id, 'rare-match');
  assert.ok(result.pages.source.links[0].score >
    result.pages.source.links.find(link => link.id === 'topic-match').score);
  assert.ok(!result.pages.source.links.some(link => link.id === 'common-match'));
});

test('distinctive topics outrank secondary overlap without filling weak slots', () => {
  const documents = [
    doc('source', {topics: ['rare', 'common']}),
    doc('specific', {topics: ['rare']}),
    doc('generic', {topics: ['common']}),
    doc('other', {topics: ['common']}),
    doc('fourth', {topics: ['common']}),
  ];
  assert.deepEqual(rankCandidates(documents, dimensions, config).pages.source.links.map(link => link.id),
    ['specific']);
});

test('portfolio recommendations preserve the reviewed relevance expectations', async () => {
  const {index} = await generate(path.resolve('.'), {url: 'https://example.com', baseUrl: '/'});
  const ids = id => index.pages[id].links.map(link => link.id);
  const taxonomy = ids('case-studies/TaxonomyGovernance');
  assert.equal(taxonomy[0], 'case-studies/RagSearchCloudArchitecture');
  assert.ok(!taxonomy.includes('skills/DocumentationLeadership'));
  assert.ok(!taxonomy.includes('skills/Agile'));
  const frameworks = ids('case-studies/DocumentingComplexDeveloperFrameworks');
  assert.equal(frameworks[0], 'case-studies/ScalingADeveloperDocsPlatform');
  assert.ok(!frameworks.includes('skills/UX'));
  assert.equal(ids('docs-samples/PaysafeDeveloperJS')[0], 'case-studies/PaysafeDeveloperCenter');
  assert.equal(ids('tools/OpenAPIandAPITools')[0], 'skills/APIDocumentation');
});

test('frontmatter control types are strict, including on disabled pages', () => {
  for (const value of [false, [], {enabled: 'false'}, {exclude: 'target'}, {exclude: null}, {prefer: ['target']},
    {enabled: false, exclude: ['unknown']}]) {
    assert.throws(() => validateOptions(value, new Set(['target']), 'source'));
  }
});

test('generation is deterministic and check reports stale artifacts without rewriting them', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'see-also-test-'));
  try {
    await fs.mkdir(path.join(root, 'docs'));
    await fs.mkdir(path.join(root, 'src/generated'), {recursive: true});
    await fs.writeFile(path.join(root, 'src/generated/taxonomy-navigation.json'), JSON.stringify({dimensions}));
    for (const document of corpus()) {
      await fs.writeFile(path.join(root, document.source),
        `---\ntitle: ${document.title}\ntype: [case-study]\ntopics: [${document.frontMatter.topics}]\n---\nArticle text.\n`);
    }
    const first = await generate(root, config);
    await writeArtifacts(root, first);
    assert.deepEqual(await generate(root, config), first);
    await writeArtifacts(root, first, true);
    await fs.appendFile(path.join(root, 'docs/source.md'), '\nA content change.');
    const changed = await generate(root, config);
    assert.notEqual(changed.index.inputHash, first.index.inputHash);
    await assert.rejects(writeArtifacts(root, changed, true), /Stale See also artifacts/);
    assert.deepEqual(JSON.parse(await fs.readFile(path.join(root, 'src/generated/see-also.json'))), first.index);
  } finally { await fs.rm(root, {recursive: true, force: true}); }
});
