const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const {serializeSummaries, validateSummary} = require('../../plugins/case-study-llms.cjs');

const filename = path.resolve(__dirname, '../../src/components/CaseStudySummary/index.tsx');
const loaded = new Module(filename, module);
loaded.paths = Module._nodeModulePaths(path.dirname(filename));
const originalRequire = loaded.require.bind(loaded);
loaded.require = name => name.endsWith('.css')
  ? {__esModule: true, default: new Proxy({}, {get: (_, key) => key})}
  : originalRequire(name);
loaded._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: {module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
    esModuleInterop: true},
}).outputText, filename);
const Summary = loaded.exports.default;
const directory = path.resolve(__dirname, '../../docs/case-studies');
const examples = fs.readdirSync(directory).filter(name => name !== 'index.md').map(name => {
  const source = fs.readFileSync(path.join(directory, name), 'utf8');
  const raw = source.match(/<CaseStudySummary \{\.\.\.(\{[\s\S]*?\})\} \/>/)?.[1];
  assert.ok(raw, `${name}: literal summary data required`);
  return {name, source, data: JSON.parse(raw)};
});
const base = examples[0].data;
const element = data => `<CaseStudySummary {...${JSON.stringify(data)}} />`;

test('six case studies render accessible, fully visible summaries before their content', () => {
  assert.equal(examples.length, 6);
  for (const {name, source, data} of examples) {
    validateSummary(data);
    const html = renderToStaticMarkup(React.createElement(Summary, data));
    assert.match(html, /<section[^>]+aria-label="Project overview"/);
    assert.match(html, /<dl class="details">/);
    assert.match(html, /class="actions" hidden=""/);
    assert.match(html, /aria-expanded="true"/);
    assert.match(html, /Skip to case study/);
    assert.match(html, /Hide summaries/);
    assert.match(html, /aria-describedby=/);
    assert.match(html, /Applies to all case studies/);
    assert.match(html, /title="Hide summaries across all case studies/);
    assert.doesNotMatch(html, /<h1|<details|tabindex|<script/);
    assert.ok(html.replace(/<[^>]*>/g, "").includes(data.summary), name);
    if (data.summaryUnderline) {
      assert.ok(html.includes(`<span class="underlined">${data.summaryUnderline}</span>`), name);
    }
    for (const {value, label} of data.evidence) {
      for (const line of value.split("\n")) assert.ok(html.includes(line), name);
      assert.ok(html.includes(label), name);
    }
    assert.ok(source.indexOf('<CaseStudySummary') < source.indexOf('\n## '), name);
    const markdown = serializeSummaries(source);
    assert.ok(markdown.includes(data.summary), name);
    assert.ok(markdown.includes(`**${data.evidenceTitle}**`), name);
    assert.ok(!markdown.includes('<CaseStudySummary'), name);
  }
});

test('one to four evidence items work with numerical and qualitative evidence', () => {
  for (let count = 1; count <= 4; count++) {
    const data = {...base, evidence: Array.from({length: count}, (_, i) => ({value: `${i + 1}`, label: 'Delivered capability'}))};
    assert.doesNotThrow(() => serializeSummaries(element(data)));
    assert.match(renderToStaticMarkup(React.createElement(Summary, data)), /Delivered capability/);
  }
  for (const evidence of [[], new Array(5).fill({value: '1', label: 'Scope'}), [{value: '', label: 'Scope'}]]) {
    assert.throws(() => serializeSummaries(element({...base, evidence})), /one to four/);
  }
});

test('numerical evidence is prominent while capability labels use quieter typography', () => {
  const data = {...base, evidence: [
    {value: '3,200+', label: 'Pages', emphasis: 'metric'},
    {value: 'Content discovery', label: 'Faceted browsing'},
  ]};
  const html = renderToStaticMarkup(React.createElement(Summary, data));
  assert.match(html, /class="metric"><dt>3,200\+<\/dt>/);
  assert.match(html, /<div><dt>Content discovery<\/dt>/);
  const exported = serializeSummaries(element(data));
  assert.ok(exported.includes('3,200+'));
  assert.ok(exported.includes('Content discovery'));
  assert.throws(() => validateSummary({...base, evidence: [{value: '1', label: 'Scope', emphasis: 'loud'}]}));
});

test('technical scope and practical benefits retain their intended meaning', () => {
  const frameworks = examples.find(({name}) => name.startsWith('Documenting'));
  const rag = examples.find(({name}) => name.startsWith('Rag'));
  const taxonomy = examples.find(({name}) => name.startsWith('Taxonomy'));
  assert.equal(frameworks.data.evidenceTitle, 'Technical Coverage');
  assert.match(serializeSummaries(frameworks.source), /Framework supporting 400,000 tests/);
  assert.equal(rag.data.evidenceNote, undefined);
  assert.equal(taxonomy.data.evidenceTitle, 'What it enables');
  assert.match(serializeSummaries(taxonomy.source), /Consistent classification/);
  assert.match(serializeSummaries(taxonomy.source), /Reliable discovery/);
  assert.match(serializeSummaries(taxonomy.source), /Controlled evolution/);
});

test('export parser handles punctuation and rejects executable expressions', () => {
  const data = {...base, summary: 'Literal {braces}, "quotes", > symbols and \\ paths.'};
  const result = serializeSummaries(`Before\n${element(data)}\nAfter`);
  assert.ok(result.startsWith('Before\n**Project overview**'));
  assert.ok(result.endsWith('\nAfter'));
  assert.match(result, /Literal \{braces\}/);
  assert.throws(() => serializeSummaries('<CaseStudySummary {...getData()} />'));
  assert.throws(() => serializeSummaries('<CaseStudySummary {...{"employer":"test"} />'));
});

test('all summary fields survive in built Markdown and the full LLM corpus', {skip: !fs.existsSync('build/llms-full.txt')}, () => {
  const full = fs.readFileSync('build/llms-full.txt', 'utf8');
  const matter = require('gray-matter');
  for (const {name, source, data} of examples) {
    const slug = matter(source).data.slug;
    const route = slug ? slug.replace(/^\//, '') : `case-studies/${name.replace(/\.md$/, '')}`;
    const exported = fs.readFileSync(`build/docs/${route}.md`, 'utf8');
    for (const text of [data.summary, data.role, data.scope, data.decision,
      data.deliverables, ...(data.evidenceNote ? [data.evidenceNote] : [])]) {
      assert.ok(exported.includes(text), `${name}: individual export missing ${text}`);
      assert.ok(full.includes(text), `${name}: full export missing ${text}`);
    }
    assert.ok(!exported.includes('<CaseStudySummary'));
  }
  assert.ok(!full.includes('<CaseStudySummary'));
});
