const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const {roles, groupStyles, prepareMermaid, flowchartWithDirection, flowchartDirection} = require('../../src/components/DiagramFigure/theme.cjs');
const {serializeDiagramFigures} = require('../../plugins/diagram-figures.cjs');

const focusFilename = path.resolve(__dirname, '../../src/components/DiagramFigure/subgraphFocus.ts');
const focusModule = new Module(focusFilename, module);
focusModule._compile(ts.transpileModule(fs.readFileSync(focusFilename, 'utf8'), {
  compilerOptions: {module: ts.ModuleKind.CommonJS},
}).outputText, focusFilename);
const {fitSubgraph, placeSubgraphNote} = focusModule.exports;

const filename = path.resolve(__dirname, '../../src/components/DiagramFigure/index.tsx');
const loaded = new Module(filename, module);
loaded.filename = filename;
loaded.paths = Module._nodeModulePaths(path.dirname(filename));
const originalRequire = loaded.require.bind(loaded);
loaded.require = name => name.endsWith('.css')
  ? {__esModule: true, default: new Proxy({}, {get: (_, key) => key})}
  : name === '@docusaurus/router' ? {
    useLocation: () => ({pathname: '/', search: ''}),
    useHistory: () => ({}),
  } : name === './subgraphFocus' ? focusModule.exports
    : name === '@theme/Heading' ? ({as, children, ...props}) => {
    return React.createElement(as, props, children);
  } : name === './context' ? {
    DiagramFigureContext: React.createContext(false),
    DiagramDirectionContext: React.createContext(undefined),
  } : originalRequire(name);
loaded._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: {module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true},
}).outputText, filename);
const Figure = loaded.exports.default;

test('subgraph notes use an adjacent space only when the diagram leaves it clear', () => {
  const rect = (left, top, width, height) => ({left, top, width, height, right: left + width, bottom: top + height});
  const frame = rect(0, 0, 800, 500);
  const target = rect(300, 120, 180, 260);
  const note = rect(0, 0, 200, 120);
  assert.deepEqual(placeSubgraphNote(frame, target, note, [target]), {
    left: 504, top: 120, connector: {left: 480, top: 180, length: 24, vertical: false},
  });
  assert.deepEqual(placeSubgraphNote(frame, target, note, [target, rect(490, 180, 1, 0)]), {
    left: 76, top: 120, connector: {left: 276, top: 180, length: 24, vertical: false},
  });
  assert.equal(placeSubgraphNote(frame, target, note, [rect(0, 0, 800, 500)]), undefined);
});

test('subgraph fit uses leading blank space only when it reveals downstream content', () => {
  const rect = (left, top, width, height) => ({left, top, width, height, right: left + width, bottom: top + height});
  const fit = (direction, target, graph) => {
    const frame = direction === 'LR' ? {clientWidth: 800, clientHeight: 600} : {clientWidth: 600, clientHeight: 800};
    const content = {style: {getPropertyValue: () => '1'},
      getBoundingClientRect: () => rect(0, 0, frame.clientWidth, frame.clientHeight)};
    const element = {
      getBoundingClientRect: () => target,
      closest: () => ({dataset: {diagramSubgraphDirection: direction}}),
      ownerSVGElement: {querySelectorAll: () => [], querySelector: () => ({getBoundingClientRect: () => graph})},
    };
    return fitSubgraph(frame, content, element);
  };
  const horizontal = rect(100, 100, 80, 300);
  const vertical = rect(100, 100, 300, 80);
  assert.ok(fit('LR', horizontal, rect(100, 100, 500, 300)).offsetX < -12);
  assert.ok(fit('TB', vertical, rect(100, 100, 300, 500)).offsetY < -12);
  assert.equal(fit('LR', horizontal, rect(-150, 100, 750, 300)).offsetX, 0);
  assert.equal(fit('TB', vertical, rect(100, 100, 300, 150)).offsetY, 0);
});

test('full-screen orientation changes the flowchart header only', () => {
  const source = '---\ntitle: Delivery\n---\n%% note\nflowchart TD\nsubgraph Delivery\ndirection TB\nA --> B\nend';
  assert.equal(flowchartWithDirection(source, 'LR'), source.replace('flowchart TD', 'flowchart LR'));
  assert.equal(flowchartWithDirection('graph LR; A --> B', 'TB'), 'graph TB; A --> B');
  assert.equal(flowchartWithDirection('sequenceDiagram\nA->>B: Hello', 'LR'), null);
  assert.equal(flowchartDirection(source), 'TB');
  assert.equal(flowchartDirection('graph RL\nA --> B'), 'LR');
  assert.equal(flowchartDirection('flowchart\nA --> B'), 'TB');
  assert.equal(flowchartWithDirection('flowchart\nA --> B', 'LR'), 'flowchart LR\nA --> B');
  assert.equal(flowchartDirection('sequenceDiagram\nA->>B: Hello'), undefined);
});

test('flowcharts with multiline init directives still support the full-screen toggle', () => {
  const source = '%%{init: {\n  "flowchart": {"nodeSpacing": 45}\n}}%%\n\nflowchart TD\nA --> B';
  assert.equal(flowchartWithDirection(source, 'LR'), source.replace('flowchart TD', 'flowchart LR'));
});

test('roles supply node icons and colors across quoted Mermaid node shapes', () => {
  const source = 'flowchart LR\nA["`fas:fa-file-lines Document`"] --> B[("Records")]\nC{"Approve?"}\nD("Service")\n'
    + 'class A input;\nclass B storage;\nclass C decision;\nclass D process;';
  const output = prepareMermaid(source);
  assert.ok(output.includes('A["`fas:fa-file-lines Document`"]'));
  assert.ok(output.includes('B[("fas:fa-database Records")]'));
  assert.ok(output.includes('C{"Approve?"}'));
  assert.ok(output.includes('D("Service")'));
  assert.ok(output.includes(`classDef input fill:${roles.input.fill},stroke:${roles.input.stroke}`));
  assert.ok(output.includes('A["`fas:fa-file-lines Document`"] --> B'));
});

test('explicit icons override defaults and other Mermaid diagrams remain unchanged', () => {
  const source = 'flowchart TD\nA["fa:fa-globe Browser"]\nclass A interaction;';
  const output = prepareMermaid(source);
  assert.ok(output.includes('fa:fa-globe Browser'));
  assert.ok(!output.includes('fa:fa-user'));
  for (const plain of ['sequenceDiagram\nAlice->>Bob: Hello', 'flowchart TD\nA --> B']) {
    assert.equal(prepareMermaid(plain), plain);
  }
});

test('containers use neutral grouping colors without changing child node semantics', () => {
  const source = 'flowchart TD\nsubgraph REVIEW["Build & review"]\nA["Build"] --> B["Reviewer"]\nend\n'
    + 'class REVIEW group-process;\nclass A process;\nclass B interaction;';
  const output = prepareMermaid(source);
  assert.ok(output.includes(`style REVIEW fill:${groupStyles.process.fill},stroke:${groupStyles.process.stroke}`));
  assert.ok(output.includes('B["fas:fa-user Reviewer"]'));
  assert.ok(output.includes(`classDef interaction fill:${roles.interaction.fill}`));
  assert.ok(!output.includes('REVIEW["fa:'));
  const groupOnly = prepareMermaid('flowchart TD\nsubgraph G["Stage"]\nA --> B\nend\nclass G group-process;');
  assert.ok(groupOnly.includes(`style G fill:${groupStyles.process.fill}`));
});

test('server-rendered figures contain accessible titles, a shared icon key and an enlargement action', () => {
  const props = {number: 2, title: 'Publishing', legend: [{role: 'input'}, {role: 'process', label: 'Build'}]};
  const html = renderToStaticMarkup(React.createElement(Figure, props, React.createElement('p', null, 'Diagram')));
  assert.match(html, /<figure[^>]+aria-labelledby=/);
  assert.match(html, /<figcaption[^>]*>Figure 2\. Publishing<\/figcaption>/);
  assert.match(html, /aria-label="Colour and icon key"/);
  assert.match(html, /fa-solid fa-file-lines/);
  assert.doesNotMatch(html, /fa-null/);
  assert.match(html, /background-color:#DCE3EA;border-color:#657789/);
  assert.match(html, /View full-screen: Figure 2\. Publishing/);
  assert.match(html, /<dialog[^>]+aria-labelledby=/);
  assert.match(html, />Inputs<\/span>/);
  assert.match(html, />Build<\/span>/);
  assert.doesNotMatch(html, /<svg/); // The enlarged render is mounted only on demand.
});

test('all site Mermaid diagrams use figures with exactly the roles their keys describe', () => {
  let diagrams = 0;
  for (const name of fs.readdirSync(path.resolve(__dirname, '../../docs'), {recursive: true})) {
    if (!/\.mdx?$/.test(name)) continue;
    const source = fs.readFileSync(path.resolve(__dirname, '../../docs', name), 'utf8');
    const fences = [...source.matchAll(/```mermaid\n([\s\S]*?)\n```/g)];
    if (!fences.length) continue;
    let covered = 0;
    for (const [, json, body] of source.matchAll(/<DiagramFigure\s+\{\.\.\.(\{[\s\S]*?\})\}\s*>([\s\S]*?)<\/DiagramFigure>/g)) {
      const props = JSON.parse(json);
      const used = new Set();
      const panelTitles = [...body.matchAll(/^#### (.+)$/gm)].map(match => match[1]);
      const expectedTitles = panelTitles.length ? panelTitles : [props.title];
      let diagramIndex = 0;
      for (const [, code] of body.matchAll(/```mermaid\n([\s\S]*?)\n```/g)) {
        covered++;
        const title = code.match(/^\s*accTitle:\s*(.+)$/m)?.[1];
        const description = code.match(/accDescr\s*\{([\s\S]*?)\}/)?.[1].trim();
        assert.equal(title, expectedTitles[diagramIndex++], `${name}: accessible name matches its existing caption or panel heading`);
        assert.ok(description, `${name}: a diagram description is required`);
        assert.doesNotMatch(code, /classDef|fa:fa-/, `${name}: use the shared theme`);
        for (const [, role] of code.matchAll(/^\s*class\s+[\w,-]+\s+([\w-]+)\s*;?\s*$/gm)) {
          if (role.startsWith('group-')) {
            assert.ok(Object.hasOwn(groupStyles, role.slice(6)), `${name}: unknown container purpose`);
            continue;
          }
          assert.ok(Object.hasOwn(roles, role), `${name}: unknown ${role}`);
          used.add(role);
        }
        const prepared = prepareMermaid(code);

        assert.match(prepared, /classDef/);
        assert.ok(prepared.includes(description), `${name}: shared theme preserves descriptions`);
      }
      assert.deepEqual([...used].sort(), props.legend.map(item => item.role).sort(), name);
      const markup = renderToStaticMarkup(React.createElement(Figure, props));
      assert.ok(markup.includes(props.title));
    }
    assert.equal(covered, fences.length, `${name}: unwrapped diagram`);
    diagrams += covered;
    const markdown = serializeDiagramFigures(source);
    assert.doesNotMatch(markdown, /<\/?DiagramFigure/);
    assert.match(markdown, /\*\*Figure 1\./);
    assert.match(markdown, /\*\*Colour and icon key\*\*/);
    assert.match(markdown, /classDef/);
    assert.equal([...markdown.matchAll(/accTitle:/g)].length, fences.length);
    assert.equal([...markdown.matchAll(/accDescr\s*\{/g)].length, fences.length);

  }
  assert.ok(diagrams > 0);
});

test('Markdown exports preserve body, default legend labels and safe literal metadata', () => {
  const props = {number: 1, title: 'Inputs <and> output', legend: [{role: 'input'}]};
  const source = `<DiagramFigure {...${JSON.stringify(props)}}>\nOriginal diagram\n</DiagramFigure>`;
  const output = serializeDiagramFigures(source);
  assert.ok(output.includes('Original diagram'));
  assert.ok(output.includes('Inputs \\<and\\> output'));
  assert.ok(output.includes('- Inputs'));
  const invalid = {...props, legend: [{role: 'unknown'}]};
  assert.throws(() => serializeDiagramFigures(`<DiagramFigure {...${JSON.stringify(invalid)}}>x</DiagramFigure>`), /valid legend/);
});
