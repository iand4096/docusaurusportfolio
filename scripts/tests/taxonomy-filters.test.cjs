const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');

const root = path.resolve(__dirname, '../..');
const catalogue = require('../../src/generated/taxonomy-navigation.json');

// Compile the actual TS/TSX modules with the repository's TypeScript dependency.
// Resolve source imports and substitute generated data and styles for server rendering.
function loadSource(relative, data = catalogue) {
  const filename = path.join(root, relative);
  const loaded = new Module(filename, module);
  loaded.paths = Module._nodeModulePaths(path.dirname(filename));
  const originalRequire = loaded.require.bind(loaded);
  loaded.require = name => {
    if (name.endsWith('taxonomy-navigation.json')) return data;
    if (name.endsWith('.css')) return {};
    if (name === '@site/src/utils/taxonomyFilters') return filters;
    if (name === './ContentTypeIcon') return loadSource('src/components/ContentTypeIcon.tsx');
    return originalRequire(name);
  };
  loaded._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
      jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true},
  }).outputText, filename);
  return loaded.exports;
}
const filters = loadSource('src/utils/taxonomyFilters.ts');

const extended = structuredClone(catalogue);
extended.dimensions.projects = {
  id: 'projects', label: 'Project', metadataField: 'project_ids',
  terms: [{id: 'portal', label: 'Portal project'}],
};
extended.dimensions.empty = {id: 'empty', label: 'Empty', metadataField: 'empty', terms: []};
extended.documents[0].project_ids = ['portal'];

test('a new taxonomy group renders automatically with its catalogue count and selection', () => {
  const {ExploreTaxonomyFilterGroups} = loadSource('src/components/ExploreTaxonomyFilterGroups.tsx', extended);
  const html = renderToStaticMarkup(React.createElement(ExploreTaxonomyFilterGroups, {
    isSelected: (id, term) => id === 'projects' && term === 'portal', onToggle: () => {},
  }));
  assert.match(html, /aria-label="Project filters"/);
  assert.match(html, /aria-pressed="true"[^>]*><span>Portal project<\/span><span>1<\/span>/);
  assert.doesNotMatch(html, /aria-label="Empty filters"/);
  assert.match(html, /aria-label="Work organisation filters"/);
});

test('Browse uses metadataField, OR within groups and AND between groups', () => {
  const selected = filters.emptyFilters(extended.dimensions);
  selected.projects.add('portal');
  selected.organisations.add('amx');
  selected.organisations.add('paysafe');
  assert.equal(filters.documentMatchesFilters({project_ids: ['portal'], organisations: ['paysafe']}, selected, extended.dimensions), true);
  assert.equal(filters.documentMatchesFilters({project_ids: ['portal'], organisations: ['mastercard']}, selected, extended.dimensions), false);
  assert.equal(filters.documentMatchesFilters({organisations: ['amx']}, selected, extended.dimensions), false);
  assert.equal(filters.emptyFilters(extended.dimensions).projects.size, 0);
});

test('URL filters handle new dimensions, repeated values and legacy contentType links', () => {
  const selected = filters.filtersFromParams(new URLSearchParams(
    'project_ids=portal&projects=invalid&organisations=amx&organisations=paysafe&contentType=case-study&view=browse',
  ), extended.dimensions);
  assert.deepEqual([...selected.projects], ['portal']);
  assert.deepEqual([...selected.organisations], ['amx', 'paysafe']);
  assert.deepEqual([...selected.content_types], ['case-study']);
});

test('Search restores only canonical values and includes new fields in request definitions', () => {
  const restored = filters.restoreFacets({project_ids: ['portal', 'invalid', 'portal'],
    organisations: 'amx', retired_field: ['old'], topics: [null, 42]}, extended.dimensions);
  assert.deepEqual(restored, {organisations: ['amx'], project_ids: ['portal']});
  assert.ok(filters.facetDefinitions(extended.dimensions).some(({key, label}) => key === 'project_ids' && label === 'Project'));
});

test('Explore hides unused facets and empty groups while retaining used terms and counts', () => {
  const data = structuredClone(extended);
  data.dimensions.projects.terms.push({id: 'unused', label: 'Unused project'});
  data.dimensions.unused = {
    id: 'unused', label: 'Unused dimension', metadataField: 'unused',
    terms: [{id: 'none', label: 'No documents'}],
  };
  data.technologyKinds['unused-kind'] = {label: 'Unused technology kind'};
  data.dimensions.technologies.terms.push({id: 'unused-tech', label: 'Unused technology', kind: 'unused-kind'});
  const {ExploreTaxonomyFilterGroups} = loadSource('src/components/ExploreTaxonomyFilterGroups.tsx', data);
  const html = renderToStaticMarkup(React.createElement(ExploreTaxonomyFilterGroups, {
    isSelected: () => false, onToggle: () => {},
  }));
  assert.doesNotMatch(html, /Unused project|Unused dimension|No documents|Unused technology/);
  assert.doesNotMatch(html, /<span>Codetreedocs<\/span>|<span>AMX Composer<\/span>/);
  assert.match(html, /<span>Portal project<\/span><span>1<\/span>/);
});

test('build coverage warnings identify unused facets without failing the build', async (t) => {
  const warnings = [];
  t.mock.method(console, 'warn', message => warnings.push(message));
  const plugin = require('../../plugins/taxonomy-coverage.cjs')({siteDir: root});
  assert.equal(await plugin.loadContent(), null);
  assert.ok(plugin.getPathsToWatch().includes(path.join(root, 'src/generated/taxonomy-navigation.json')));
  for (const dimension of Object.values(catalogue.dimensions)) {
    for (const term of dimension.terms) {
      const count = catalogue.documents.filter(document =>
        (document[dimension.metadataField] ?? []).includes(term.id)).length;
      const warning = warnings.find(message => message.includes(`${dimension.id}.${term.id} (`));
      assert.equal(Boolean(warning), count === 0, `${dimension.id}.${term.id}`);
      if (warning) assert.ok(warning.includes(term.label) && warning.includes('hidden from Explore'));
    }
  }
  assert.ok(warnings.some(message => message.includes('Codetreedocs')));
  assert.ok(warnings.some(message => message.includes('AMX Composer')));
});

test('metadata toggle exposes its state, target and selected count with a decorative icon', () => {
  const {default: Toggle} = loadSource('src/components/MetadataFilterToggle.tsx');
  for (const visible of [false, true]) {
    const html = renderToStaticMarkup(React.createElement(Toggle, {
      visible, onToggle: () => {}, controls: 'taxonomy-options', count: 2,
    }));
    assert.ok(html.includes(`aria-expanded="${visible}"`));
    assert.match(html, /aria-controls="taxonomy-options"/);
    assert.ok(html.includes(`${visible ? 'Hide' : 'Show'} filters (2 selected)`));
    assert.match(html, /<svg[^>]*aria-hidden="true"/);
    assert.match(html, /<button type="button"/);
  }
});

test('filter visibility starts hidden during server rendering', () => {
  const {useMetadataFilterVisibility} = loadSource('src/components/MetadataFilterToggle.tsx');
  function Probe() {
    const [visible] = useMetadataFilterVisibility();
    return React.createElement('div', {'data-visible': String(visible)});
  }
  assert.match(renderToStaticMarkup(React.createElement(Probe)), /data-visible="false"/);
});
