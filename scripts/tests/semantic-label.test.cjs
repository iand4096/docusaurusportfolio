const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');

// Exercise the real JSX with the installed compiler; CSS names remain inspectable.
const filename = path.resolve(__dirname, '../../src/components/SemanticLabel/index.jsx');
const loaded = new Module(filename, module);
loaded.paths = Module._nodeModulePaths(path.dirname(filename));
const originalRequire = loaded.require.bind(loaded);
loaded.require = name => name.endsWith('.css')
  ? {__esModule: true, default: new Proxy({}, {get: (_, key) => key})}
  : originalRequire(name);
loaded._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: {module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
    allowJs: true, esModuleInterop: true},
}).outputText, filename);
const {default: SemanticLabel, SemanticLabelGroup} = loaded.exports;
const render = (props = {}, children = 'Supporting text.') =>
  renderToStaticMarkup(React.createElement(SemanticLabel, props, children));

test('all semantic types retain visible meaning and the specified decorative icon', () => {
  for (const [type, label, icon] of [
    ['decision', 'Decision', 'compass'],
    ['rationale', 'Rationale', 'lightbulb'],
    ['constraint', 'Constraint', 'lock'],
    ['trade-off', 'Trade-off', 'scale-balanced'],
    ['risk', 'Risk', 'triangle-exclamation'],
    ['outcome', 'Outcome', 'circle-check'],
    ['contribution', 'Contribution', 'pen-to-square'],
    ['validation', 'Validation', 'clipboard-check'],
  ]) {
    for (const appearance of ['row', 'accent']) {
      const html = render({type, appearance});
      assert.ok(html.includes(`</i>${label}</strong>`), html);
      assert.ok(html.includes(`fa-solid fa-${icon} icon`), html);
      assert.ok(html.includes('aria-hidden="true"'), html);
      assert.ok(html.includes(` ${appearance}"`), html);
      assert.doesNotMatch(html, /<h[1-6]|<button|role="button"/);
    }
    const inline = render({type});
    assert.ok(inline.includes(`${label}:</strong>`), inline);
    assert.doesNotMatch(inline, /<i\b/);
  }
});

test('defaults and unknown values safely select known styles and labels', () => {
  const expected = render();
  for (const invalid of ['unknown', '__proto__', 'constructor', 'toString',
    'risk arbitrary-class', null, {}, 42]) {
    assert.equal(render({type: invalid, appearance: invalid}), expected);
  }
  assert.ok(expected.includes('Decision:</strong>'));
  assert.ok(expected.includes('root decision inline'));
});

test('inline content and MDX paragraph children retain valid containers and escaping', () => {
  const content = React.createElement('p', null,
    'Keep ', React.createElement('em', null, 'structured content'), ' and ',
    React.createElement('a', {href: '#approach'}, 'links'), '.');
  for (const appearance of ['inline', 'row', 'accent']) {
    const html = render({appearance}, content);
    assert.ok(html.includes('<div class="content"><p>Keep <em>structured content</em>'), html);
    assert.ok(html.includes('<a href="#approach">links</a>'), html);
  }
  const longText = '<script>alert(1)</script> ' + 'LongTechnicalTerm'.repeat(30);
  assert.ok(render({}, longText).includes('&lt;script&gt;alert(1)&lt;/script&gt;'));
  assert.ok(render({}, longText).includes('LongTechnicalTerm'.repeat(30)));
});

test('related rows share a plain group without additional headings or interactive semantics', () => {
  const html = renderToStaticMarkup(React.createElement(SemanticLabelGroup, null,
    React.createElement(SemanticLabel, {type: 'decision', appearance: 'row'}, 'Use one source.'),
    React.createElement(SemanticLabel, {type: 'rationale', appearance: 'row'}, 'Avoid duplication.')));
  assert.ok(html.startsWith('<div class="group"><div class="root decision row">'), html);
  assert.ok(html.includes('Use one source.'));
  assert.ok(html.includes('Avoid duplication.'));
  assert.equal((html.match(/class="root /g) || []).length, 2);
  assert.doesNotMatch(html, /<h[1-6]|role=|<button/);
});
