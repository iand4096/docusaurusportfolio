// Optional browser regression check using an existing Playwright installation.
// See src/components/DiagramFigure/README.md for the tool and server settings.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const {roles, groupStyles} = require('../../src/components/DiagramFigure/theme.cjs');

const base = process.env.DIAGRAM_BASE_URL || 'http://localhost:3000/docusaurusportfolio';
const output = process.env.DIAGRAM_SCREENSHOTS;
const pages = [
  ['case-studies/scalingdeveloperdocs', 1, 'case-studies/ScalingADeveloperDocsPlatform.md'],
  ['case-studies/RagSearchCloudArchitecture', 3, 'case-studies/RagSearchCloudArchitecture.md'],
  ['case-studies/paysafedevcenter', 1, 'case-studies/PaysafeDeveloperCenter.md'],
  ['implementation-details/taxonomy', 2, 'implementation-details/taxonomy.md'],
  ['misc/OptimusRICE', 1, 'misc/OptimusRICE.md'],
];
const matrix = [[1440, 'light'], [1024, 'light'], [768, 'light'], [390, 'light'],
  [320, 'light'], [1440, 'dark'], [390, 'dark']];

async function checkDescriptions(container, expected) {
  const actual = await container.locator('svg').evaluateAll(svgs => svgs.map(svg => {
    const referenced = attribute => (svg.getAttribute(attribute) || '').split(/\s+/).filter(Boolean).map(id => {
      const element = document.getElementById(id);
      return element && svg.contains(element) && document.querySelectorAll('#' + CSS.escape(id)).length === 1
        ? element.textContent.replace(/\s+/g, ' ').trim() : '';
    }).join(' ');
    return {title: referenced('aria-labelledby'), description: referenced('aria-describedby')};
  }));
  assert.deepEqual(actual, expected, 'Each SVG has its own linked accessible title and description');
}

async function checkSharedLinks(browser) {
  const context = await browser.newContext({permissions: ['clipboard-read', 'clipboard-write']});
  try {
    const source = await context.newPage();
    await source.goto(`${base}/docs/case-studies/RagSearchCloudArchitecture`);
    const anchor = '#diagram-documentation-indexing-and-search';
    const figure = source.locator('figure').filter({has: source.locator(anchor)});
    const permalink = figure.getByRole('link', {name: 'Direct link to Figure 1. Documentation indexing and search'});
    await figure.locator(anchor).hover();
    await permalink.click();
    await source.waitForURL(url => url.hash === anchor && !url.search);
    assert.equal(await figure.getByRole('dialog').count(), 0);
    await figure.getByRole('button', {name: /^View full-screen/}).click();
    const viewer = figure.getByRole('dialog');
    const copy = viewer.getByRole('button', {name: 'Copy diagram link'});
    await viewer.getByRole('button', {name: 'Search and answer generation', exact: true}).click();
    await viewer.getByRole('button', {name: 'Left to right', exact: true}).click();
    await viewer.getByRole('button', {name: 'Zoom in', exact: true}).click();
    await copy.click();
    await viewer.getByText('Link copied', {exact: true}).waitFor();
    const link = new URL(await source.evaluate(() => navigator.clipboard.readText()));
    assert.equal(link.hash, '#diagram-documentation-indexing-and-search');
    assert.deepEqual(Object.fromEntries(link.searchParams), {
      diagram: 'documentation-indexing-and-search', panel: 'search-and-answer-generation', layout: 'lr',
    });

    const recipient = await context.newPage();
    await recipient.setViewportSize({width: 390, height: 800});
    await recipient.goto(link.href);
    const opened = recipient.getByRole('dialog', {name: 'Figure 1. Documentation indexing and search'});
    await opened.locator('svg:visible').waitFor();
    assert.match(await opened.locator('svg:visible title').textContent(), /Search and answer generation/);
    assert.equal(await opened.getByRole('button', {name: 'Top to bottom'}).count(), 1);
    assert.equal(await opened.getByRole('button', {name: 'Reset zoom and fit diagram'}).textContent(), '100%');
    await recipient.keyboard.press('Escape');
    await opened.waitFor({state: 'hidden'});
    await recipient.waitForURL(url => !url.search && url.hash === link.hash);
    const inline = recipient.locator('figure').filter({has: recipient.locator(link.hash)});
    assert.equal(await inline.getByRole('button', {name: /^View full-screen/})
      .evaluate(button => document.activeElement === button), true);

    await viewer.getByRole('button', {name: 'All diagrams', exact: true}).click();
    await source.evaluate(() => {
      Object.defineProperty(navigator, 'clipboard', {
        configurable: true,
        value: {writeText: async () => { throw new Error('Clipboard denied'); }},
      });
    });
    await copy.click();
    const fallback = viewer.getByRole('textbox', {name: 'Diagram link'});
    await fallback.waitFor();
    await source.waitForFunction(() => {
      const field = document.activeElement;
      return field instanceof HTMLInputElement && field.selectionStart === 0 && field.selectionEnd === field.value.length;
    });
    const allLink = new URL(await fallback.inputValue());
    assert.equal(allLink.searchParams.has('panel'), false);
    await recipient.goto(allLink.href);
    await opened.getByRole('button', {name: 'All diagrams', pressed: true}).waitFor();
    await recipient.waitForFunction(() => document.querySelectorAll('dialog[open] svg').length === 2);
    console.log('Diagram share links, clipboard fallback and anchor on close passed.');

    await opened.locator('svg:visible').first().dblclick({position: {x: 2, y: 2}});
    await opened.waitFor({state: 'hidden'});
    const open = inline.getByRole('button', {name: /^View full-screen/});
    assert.match(await open.getAttribute('title'), /double-click the diagram to open or close/i);
    await inline.locator('svg:visible').first().dblclick({position: {x: 2, y: 2}});
    await opened.getByRole('button', {name: 'Indexing before deployment', pressed: true}).waitFor();
    await opened.locator('svg:visible').first().dblclick({position: {x: 2, y: 2}});
    await opened.waitFor({state: 'hidden'});
    assert.equal(await open.evaluate(button => document.activeElement === button), true);
    console.log('Double-clicking a diagram opens and closes the full-screen viewer.');
  } finally {
    await context.close();
  }
}

async function checkLayoutDefaults(browser) {
  const page = await browser.newPage({viewport: {width: 390, height: 800}});
  try {
    const url = new URL(`${base}/docs/case-studies/RagSearchCloudArchitecture`);
    const figureId = 'documentation-indexing-and-search';
    const figure = page.locator('figure').filter({has: page.locator(`#diagram-${figureId}`)});
    const viewer = figure.getByRole('dialog');
    const open = figure.getByRole('button', {name: /^View full-screen/});
    const save = viewer.getByRole('button', {name: 'Set as default'});
    const horizontal = viewer.getByRole('button', {name: 'Left to right', exact: true});
    const vertical = viewer.getByRole('button', {name: 'Top to bottom', exact: true});
    await page.goto(url.href);
    await open.click();
    await viewer.getByRole('button', {name: 'Search and answer generation', exact: true}).click();
    await horizontal.waitFor();
    assert.equal(await save.count(), 0, 'The authored layout is already the default');
    await horizontal.click();
    assert.equal(await save.getAttribute('title'), 'Use this layout when opening this figure full-screen.');
    await save.click();
    await viewer.getByRole('status').getByText('Left to right saved as default.').waitFor();
    assert.equal(await save.count(), 0, 'The just-saved layout is now the default');
    await vertical.click();
    await page.keyboard.press('Escape');
    await viewer.waitFor({state: 'hidden'});

    await page.reload();
    await open.click();
    await viewer.getByRole('button', {name: 'All diagrams', pressed: true}).waitFor();
    await vertical.waitFor();
    assert.equal(await save.count(), 0, 'The stored default persists after reload');
    await viewer.getByRole('button', {name: 'Indexing before deployment', exact: true}).click();
    await vertical.waitFor();

    const shared = new URL(url);
    shared.search = new URLSearchParams({diagram: figureId, panel: 'search-and-answer-generation', layout: 'tb'});
    await page.goto(shared.href);
    await viewer.getByRole('button', {name: 'Search and answer generation', pressed: true}).waitFor();
    await horizontal.waitFor();
    await page.evaluate(() => {
      const setItem = Storage.prototype.setItem;
      Storage.prototype.setItem = function (key, value) {
        if (key.startsWith('diagram-fullscreen-layout:')) throw new Error('Storage denied');
        return setItem.call(this, key, value);
      };
    });
    await save.click();
    await viewer.getByRole('status').getByText('Could not save the layout preference in this browser.').waitFor();
    await horizontal.waitFor();
    await page.keyboard.press('Escape');
    await viewer.waitFor({state: 'hidden'});
    await open.click();
    await vertical.waitFor();
    await page.keyboard.press('Escape');
    await viewer.waitFor({state: 'hidden'});

    const other = page.locator('figure').filter({has: page.locator('#diagram-azure-deployment-architecture')});
    await other.getByRole('button', {name: /^View full-screen/}).click();
    await other.getByRole('dialog').getByRole('button', {name: 'Left to right', exact: true}).waitFor();
    console.log('Per-figure layout defaults, share-link priority and blocked storage passed.');
  } finally {
    await page.close();
  }
}

async function checkSubgraphZoom(browser) {
  const context = await browser.newContext({permissions: ['clipboard-read', 'clipboard-write']});
  try {
    const page = await context.newPage();
    const url = new URL(`${base}/docs/case-studies/RagSearchCloudArchitecture`);
    const figureId = 'azure-deployment-architecture';
    const figure = page.locator('figure').filter({has: page.locator(`#diagram-${figureId}`)});
    const viewer = figure.getByRole('dialog');
    const zoomTo = viewer.getByRole('combobox', {name: 'Zoom to'});
    const waitForVisualOrder = direction => page.waitForFunction(direction => {
      const viewer = document.querySelector('dialog[open]');
      const diagram = viewer?.querySelector(`[data-diagram-subgraph-direction="${direction}"]`);
      const menu = viewer?.querySelector('select');
      if (!diagram || !menu) return false;
      const visualOrder = [...diagram.querySelectorAll('g.cluster')].map(cluster => {
        const {left, top} = cluster.getBoundingClientRect();
        return {left, top, label: cluster.querySelector('.cluster-label').textContent.replace(/\s+/g, ' ').trim()};
      }).sort((a, b) => direction === 'LR' ? a.left - b.left || a.top - b.top : a.top - b.top || a.left - b.left)
        .map(cluster => cluster.label);
      const menuOrder = [...menu.options].filter(option => option.value).map(option => option.textContent.trim());
      return visualOrder.length === 2 && JSON.stringify(visualOrder) === JSON.stringify(menuOrder);
    }, direction);
    const waitForSubgraphFit = (id = 'PACKAGE') => page.waitForFunction(id => {
      const stage = document.querySelector('dialog[open] [aria-label^="Diagram viewport:"]');
      const group = [...(stage?.querySelectorAll('g.cluster[id]') ?? [])]
        .find(cluster => cluster.id === id || cluster.id.endsWith('-' + id));
      if (!group) return false;
      const frame = stage.getBoundingClientRect();
      const target = group.getBoundingClientRect();
      const outline = stage.querySelector('[data-subgraph-highlight]')?.getBoundingClientRect();
      const horizontal = group.closest('[data-diagram-subgraph-direction]').dataset.diagramSubgraphDirection === 'LR';
      const root = group.ownerSVGElement.querySelector('g.root')?.getBoundingClientRect();
      const centredMargin = ((horizontal ? stage.clientWidth : stage.clientHeight)
        - (horizontal ? target.width : target.height)) / 2;
      const padding = Math.min(16, stage.clientWidth / 10, stage.clientHeight / 10);
      const startContext = root ? (horizontal ? target.left - root.left : target.top - root.top) : 0;
      const endContext = root ? (horizontal ? root.right - target.right : root.bottom - target.bottom) : 0;
      const possibleShift = Math.min(centredMargin - Math.max(0, startContext) - padding, endContext - centredMargin);
      const expectedShift = possibleShift >= 12 ? possibleShift : 0;
      const offsetX = target.left + target.width / 2 - frame.left - frame.width / 2;
      const offsetY = target.top + target.height / 2 - frame.top - frame.height / 2;
      return target.width > 0 && target.height > 0
        && Math.abs(offsetX + (horizontal ? expectedShift : 0)) < 2
        && Math.abs(offsetY + (horizontal ? 0 : expectedShift)) < 2
        && target.width <= frame.width - 4 && target.height <= frame.height - 4
        && target.left >= frame.left + 4 && target.top >= frame.top + 4
        && target.right <= frame.right - 4 && target.bottom <= frame.bottom - 4
        && (outline ? Math.abs(outline.left - target.left) < 1 && Math.abs(outline.top - target.top) < 1
          && Math.abs(outline.width - target.width) < 1 && Math.abs(outline.height - target.height) < 1
          : Math.min(frame.width - target.width, frame.height - target.height) < 36);
    }, id);

    await page.setViewportSize({width: 1440, height: 900});
    await page.goto(url.href);
    await figure.getByRole('button', {name: /^View full-screen/}).click();
    await waitForVisualOrder('TB');
    await zoomTo.getByRole('option', {name: 'Choose a subgraph', exact: true}).waitFor({state: 'attached'});
    assert.equal(await zoomTo.getByRole('option', {name: 'Whole diagram', exact: true}).count(), 0);
    await zoomTo.selectOption({label: 'Static frontend'});
    await waitForSubgraphFit('FRONTEND');
    const desktopNote = viewer.getByRole('complementary', {name: 'About Static frontend'});
    await desktopNote.waitFor();
    assert.match(await desktopNote.textContent(), /GitHub Pages/);
    const noteBox = await desktopNote.boundingBox();
    const canvasBox = await viewer.getByRole('region', {name: /^Diagram viewport:/}).boundingBox();
    assert.equal(await desktopNote.getByText('About Static frontend', {exact: true}).isVisible(), false);
    assert.equal(await viewer.locator('[data-note-connector]').evaluate(line => getComputedStyle(line).borderTopStyle), 'dashed');
    const groupBox = await viewer.locator('g.cluster[id="FRONTEND"], g.cluster[id$="-FRONTEND"]').boundingBox();
    assert.ok(noteBox.x >= canvasBox.x && noteBox.y >= canvasBox.y
      && noteBox.x + noteBox.width <= canvasBox.x + canvasBox.width
      && noteBox.y + noteBox.height <= canvasBox.y + canvasBox.height);
    assert.ok(noteBox.x >= groupBox.x + groupBox.width || noteBox.x + noteBox.width <= groupBox.x
      || noteBox.y >= groupBox.y + groupBox.height || noteBox.y + noteBox.height <= groupBox.y);
    assert.equal(await desktopNote.evaluate(note => getComputedStyle(note).fontSize), '16px');
    await viewer.locator('[data-subgraph-highlight]').waitFor();
    const largestLabel = await viewer.locator('g.cluster[id="FRONTEND"], g.cluster[id$="-FRONTEND"]').evaluate(group => {
      const bounds = group.getBoundingClientRect();
      return Math.max(0, ...[...group.ownerSVGElement.querySelectorAll('g.node .nodeLabel')].map(label => {
        const rect = label.getBoundingClientRect();
        const x = rect.left + rect.width / 2, y = rect.top + rect.height / 2;
        if (x < bounds.left || x > bounds.right || y < bounds.top || y > bounds.bottom) return 0;
        const matrix = (label.closest('foreignObject') || label).getScreenCTM();
        return parseFloat(getComputedStyle(label).fontSize) * Math.hypot(matrix.a, matrix.b);
      }));
    });
    assert.ok(Math.abs(largestLabel - 24) < 0.5, `Capped label size: ${largestLabel}px`);
    const zoomIn = viewer.getByRole('button', {name: 'Zoom in', exact: true});
    const zoomOut = viewer.getByRole('button', {name: 'Zoom out', exact: true});
    const connector = viewer.locator('[data-note-connector]');
    for (let i = 0; i < 8; i++) await zoomIn.click();
    await desktopNote.waitFor({state: 'hidden'});
    assert.equal((await viewer.getByRole('region', {name: /^Diagram viewport:/}).boundingBox()).width, canvasBox.width);
    assert.equal(await connector.count(), 0);
    for (let i = 0; i < 16; i++) await zoomOut.click();
    await connector.waitFor({state: 'visible'});
    assert.equal(await zoomTo.locator('option:checked').textContent(), 'Static frontend');
    await zoomTo.selectOption({label: 'Backend packaging & image publishing'});
    await waitForSubgraphFit();
    await viewer.getByRole('button', {name: 'Left to right', exact: true}).click();
    await waitForSubgraphFit();
    await waitForVisualOrder('LR');
    await viewer.getByRole('button', {name: 'Copy diagram link'}).click();
    await viewer.getByText('Link copied', {exact: true}).waitFor();
    const link = new URL(await page.evaluate(() => navigator.clipboard.readText()));
    assert.equal(link.searchParams.get('subgraph'), 'PACKAGE');
    assert.equal(link.searchParams.get('layout'), 'lr');

    await page.setViewportSize({width: 390, height: 800});
    await page.goto(link.href);
    await waitForSubgraphFit();
    assert.equal(await zoomTo.locator('option:checked').textContent(), 'Backend packaging & image publishing');
    const mobileNote = viewer.locator('details').filter({hasText: 'About Backend packaging & image publishing'});
    assert.equal(await mobileNote.getAttribute('open'), null);
    const noteSummary = mobileNote.locator('summary');
    await noteSummary.focus();
    await page.keyboard.press('Enter');
    await mobileNote.locator('p').waitFor();
    assert.match(await mobileNote.locator('p').textContent(), /prebuilt search index/);
    await waitForSubgraphFit();
    await zoomTo.selectOption({label: 'Whole diagram'});
    assert.equal(await mobileNote.count(), 0);
    assert.equal(await zoomTo.inputValue(), '');
    assert.equal(await zoomTo.getByRole('option', {name: 'Whole diagram', exact: true}).count(), 0);
    await page.keyboard.press('Escape');
    await page.waitForURL(current => !current.search);
    link.searchParams.set('subgraph', 'REMOVED');
    await page.goto(link.href);
    await zoomTo.waitFor();
    assert.equal(await zoomTo.inputValue(), '');
    console.log('Subgraph fit, layout changes, share links and missing-target fallback passed.');
  } finally {
    await context.close();
  }
}

async function checkNotePlacementAfterSelection(browser) {
  const page = await browser.newPage({viewport: {width: 1920, height: 1080}});
  try {
    await page.goto(`${base}/docs/case-studies/paysafedevcenter`);
    const figure = page.locator('figure').filter({has: page.locator('#diagram-developer-center-authoring-and-publishing')});
    await figure.getByRole('button', {name: /^View full-screen/}).click();
    const viewer = figure.getByRole('dialog');
    const zoomTo = viewer.getByRole('combobox', {name: 'Zoom to'});
    const connector = viewer.locator('[data-note-connector]');
    const mergeNote = viewer.getByRole('complementary', {name: 'About Merge & automated build'});

    await zoomTo.selectOption({label: 'Merge & automated build'});
    await mergeNote.waitFor();
    await connector.waitFor();
    await zoomTo.selectOption({label: 'Build & review'});
    await viewer.getByRole('complementary', {name: 'About Build & review'}).waitFor();
    await zoomTo.selectOption({label: 'Merge & automated build'});
    await mergeNote.waitFor();
    await connector.waitFor({timeout: 5000});
    const viewport = viewer.getByRole('region', {name: /^Diagram viewport:/});
    const pan = key => viewport.evaluate((region, key) => {
      for (let i = 0; i < 60; i++) {
        region.dispatchEvent(new KeyboardEvent('keydown', {key, bubbles: true, cancelable: true}));
      }
    }, key);
    await pan('ArrowRight');
    await mergeNote.waitFor({state: 'hidden'});
    await connector.waitFor({state: 'hidden'});
    assert.equal(await zoomTo.locator('option:checked').textContent(), 'Merge & automated build');
    await pan('ArrowLeft');
    await mergeNote.waitFor();
    await connector.waitFor();
    const frame = await viewport.boundingBox();
    const x = frame.x + frame.width - 30;
    const y = frame.y + frame.height - 30;
    await page.mouse.move(x, y);
    await page.mouse.down();
    for (const fraction of [0.35, 0.46, 0.55, 0.61, 0.65, 0.7]) {
      await page.mouse.move(x - frame.width * fraction, y);
      assert.equal((await viewport.boundingBox()).width, frame.width, 'Dragging must preserve the canvas width');
    }
    await mergeNote.waitFor({state: 'hidden'});
    await page.mouse.move(x, y, {steps: 10});
    await connector.waitFor();
    await page.mouse.up();
    console.log('The merge note stays linked across selections and the canvas keeps its width during dragging.');
  } finally {
    await page.close();
  }
}

(async () => {
  if (output) fs.mkdirSync(output, {recursive: true});
  const browser = await chromium.launch({headless: true,
    executablePath: process.env.CHROMIUM_EXECUTABLE || undefined,
    env: {PATH: process.env.PATH, HOME: os.tmpdir(),
      LD_LIBRARY_PATH: process.env.DIAGRAM_BROWSER_LIBRARY_PATH || ''}});
  const report = [];
  try {
    await checkSharedLinks(browser);
    await checkLayoutDefaults(browser);
    await checkSubgraphZoom(browser);
    await checkNotePlacementAfterSelection(browser);
    for (const [width, theme] of matrix) {
      const context = await browser.newContext({viewport: {width, height: 900},
        colorScheme: theme, isMobile: width <= 390});
      await context.addInitScript(value => localStorage.setItem('theme', value), theme);
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      for (const [route, count, sourcePath] of pages) {
        const source = fs.readFileSync(path.resolve(__dirname, '../../docs', sourcePath), 'utf8');
        const descriptions = [...source.matchAll(/accTitle:\s*([^\n]+)\s*\n\s*accDescr\s*\{([\s\S]*?)\}/g)]
          .map(([, title, description]) => ({title: title.trim(), description: description.replace(/\s+/g, ' ').trim()}));
        assert.equal(descriptions.length, count);
        const groupPurposes = Object.fromEntries([...source.matchAll(/^\s*class\s+([\w,-]+)\s+group-(\w+)\s*;?\s*$/gm)]
          .flatMap(([, ids, purpose]) => ids.split(',').map(id => [id, purpose])));
        const response = await page.goto(`${base}/docs/${route}`);
        assert.equal(response.status(), 200, route);
        await page.waitForFunction(expected => document.querySelectorAll('figure svg').length === expected, count);
        await page.evaluate(() => document.fonts.ready);
        await checkDescriptions(page.locator('figure'), descriptions);
        const metrics = await page.locator('figure').evaluateAll((figures, theme) => {
          const palette = theme.roles;
          const rgb = hex => `rgb(${[1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16)).join(', ')})`;
          return figures.map(figure => ({
            title: figure.querySelector('figcaption').textContent,
            width: figure.getBoundingClientRect().width,
            overflow: document.documentElement.scrollWidth > innerWidth + 1,
            groups: [...figure.querySelectorAll('svg .cluster')].map(group => {
              // Mermaid prefixes group IDs but does not preserve their classes.
              const id = Object.keys(theme.groupPurposes).find(id => group.id === id || group.id.endsWith(`-${id}`));
              const purpose = theme.groupPurposes[id];
              return {id: group.id, purpose, fill: getComputedStyle(group.querySelector('rect')).fill,
                colored: !!purpose && getComputedStyle(group.querySelector('rect')).fill === rgb(theme.groupStyles[purpose].fill)};
            }),
            nodes: [...figure.querySelectorAll('svg .node')].map(node => {
              const role = [...node.classList].find(name => palette[name]);
              const icon = node.querySelector('i');
              return {role, colored: role && getComputedStyle(node.querySelector('rect, polygon, path, circle, ellipse')).fill === rgb(palette[role].fill),
                icon: role && (palette[role].icon
                  ? !!icon && icon.classList.contains(`fa-${palette[role].icon}`)
                    && getComputedStyle(icon, '::before').content !== 'none'
                    && getComputedStyle(icon).fontFamily.includes('Font Awesome')
                  : !icon)};
            }),
            fonts: [...figure.querySelectorAll('svg')].map(svg =>
              parseFloat(getComputedStyle(svg.querySelector('.nodeLabel')).fontSize) * svg.getScreenCTM().a),
            panels: [...figure.querySelectorAll('.diagram-panel')].map(panel => {
              const box = panel.getBoundingClientRect();
              return {x: box.x, y: box.y, title: panel.querySelector('h4').textContent};
            }),
          }));
        }, {roles, groupStyles, groupPurposes});
        for (const metric of metrics) {
          assert.equal(metric.overflow, false, `${route}: page overflow at ${width}`);
          assert.ok(metric.groups.every(group => group.colored), `${route}: incorrect purpose tint: ${JSON.stringify(metric.groups)}`);
          assert.ok(metric.nodes.length && metric.nodes.every(node => node.colored && node.icon),
            `${route}: missing node colors or icons at ${width}: ${JSON.stringify(metric.nodes)}`);
          const minimumFont = metric.panels.length && metric.width >= 768 ? 12 : 14;
          assert.ok(metric.fonts.every(size => size >= minimumFont), `${route}: unreadable text at ${width}: ${metric.fonts}`);
          if (metric.panels.length) {
            assert.equal(metric.panels.length, 2);
            assert.match(metric.panels[0].title, /Indexing before deployment/);
            assert.match(metric.panels[1].title, /Search and answer generation/);
            if (metric.width >= 768) {
              assert.ok(Math.abs(metric.panels[0].y - metric.panels[1].y) < 1, 'Desktop panels align');
              assert.ok(metric.panels[1].x > metric.panels[0].x, 'Desktop panels are side by side');
            } else {
              assert.ok(metric.panels[1].y > metric.panels[0].y, 'Narrow panels stack');
            }
          }
        }
        // Exercise every figure, including the multi-diagram RAG figure, in full-screen view.
        {
          const figures = page.locator('figure');
          for (let i = 0; i < await figures.count(); i++) {
            const figure = figures.nth(i);
            const expected = await figure.locator('svg').count();
            const figureTitles = await figure.locator('svg').evaluateAll(svgs => svgs.map(svg => svg.querySelector('title').textContent.trim()));
            const figureDescriptions = descriptions.filter(item => figureTitles.includes(item.title));
            const button = figure.getByRole('button', {name: /^View full-screen: Figure/});
            if (output) await figure.screenshot({path: path.join(output, `${route.split('/').pop()}-${i}-${width}-${theme}.png`),
              style: '.navbar {visibility: hidden}'});
            await button.click();
            const dialog = figure.locator('dialog');
            await dialog.waitFor({state: 'visible'});
            await page.waitForFunction(count => document.querySelectorAll('dialog[open] svg').length === count, expected);
            await checkDescriptions(dialog, figureDescriptions);
            const modal = await dialog.evaluate(element => {
              const box = element.getBoundingClientRect();
              return {x: box.x, y: box.y, width: box.width, height: box.height,
                viewportWidth: innerWidth, viewportHeight: innerHeight,
                headings: element.querySelectorAll('.diagram-panel h4').length};
            });
            assert.ok(Math.abs(modal.x) < 1 && Math.abs(modal.y) < 1);
            assert.ok(Math.abs(modal.width - modal.viewportWidth) < 1, 'Fullscreen width');
            assert.ok(Math.abs(modal.height - modal.viewportHeight) < 1, 'Fullscreen height');
            assert.equal(modal.headings, route.includes('RagSearch') && i === 0 ? 2 : 0);
            if (modal.headings > 1) {
              await dialog.getByRole('group', {name: 'Diagrams in this figure'}).waitFor();
              assert.equal(await dialog.locator('.diagram-panel h4:visible').count(), 2);
            }
            assert.equal(await dialog.getByRole('list', {name: 'Colour and icon key'}).count(), 1);
            if (output) await page.screenshot({path: path.join(output, `${route.split('/').pop()}-${i}-${width}-${theme}-fullscreen.png`)});
            const viewport = dialog.getByLabel(/^Diagram viewport:/);
            const zoomLevel = dialog.getByRole('button', {name: 'Reset zoom and fit diagram'});
            const zoomIn = dialog.getByRole('button', {name: 'Zoom in', exact: true});
            const zoomOut = dialog.getByRole('button', {name: 'Zoom out', exact: true});
            assert.match(await zoomIn.getAttribute('title'), /mouse wheel/);
            assert.match(await zoomOut.getAttribute('title'), /mouse wheel/);
            assert.equal(await zoomLevel.textContent(), '100%');
            const waitForFit = count => page.waitForFunction(count => {
              const frame = document.querySelector('dialog[open] [aria-label^="Diagram viewport:"]');
              const content = frame.firstElementChild;
              if (content.querySelectorAll('svg:not([hidden] *)').length !== count) return false;
              const outer = frame.getBoundingClientRect();
              const inner = content.getBoundingClientRect();
              const centeredPanels = [...content.querySelectorAll('.diagram-panel')].every(panel => {
                if (count === 1) return true;
                const area = panel.getBoundingClientRect();
                const graph = panel.querySelector('svg').getBoundingClientRect();
                return Math.abs(graph.left + graph.width / 2 - area.left - area.width / 2) < 1
                  && Math.abs(graph.top + graph.height / 2 - area.top - area.height / 2) < 1;
              });
              return inner.width <= outer.width && inner.height <= outer.height
                && Math.min(outer.width - inner.width, outer.height - inner.height) < 3
                && Math.abs(inner.left + inner.width / 2 - outer.left - outer.width / 2) < 1
                && Math.abs(inner.top + inner.height / 2 - outer.top - outer.height / 2) < 1
                && centeredPanels;
            }, count);
            await waitForFit(expected);
            const transform = () => viewport.evaluate(element => {
              const content = element.firstElementChild;
              const matrix = new DOMMatrix(getComputedStyle(content).transform);
              const frame = element.getBoundingClientRect();
              const diagram = content.getBoundingClientRect();
              return {zoom: matrix.a, x: diagram.left - frame.left, y: diagram.top - frame.top,
                cx: frame.width / 2, cy: frame.height / 2};
            });
            const before = await transform();
            await zoomIn.click();
            assert.equal(await zoomLevel.textContent(), '120%');
            const after = await transform();
            assert.ok(Math.abs((before.cx - before.x) * after.zoom / before.zoom - (after.cx - after.x)) < 0.2,
              'Zoom keeps the horizontal midpoint fixed');
            assert.ok(Math.abs((before.cy - before.y) * after.zoom / before.zoom - (after.cy - after.y)) < 0.2,
              'Zoom keeps the vertical midpoint fixed');
            await zoomOut.click();
            assert.equal(await zoomLevel.textContent(), '100%');
            const box = await viewport.boundingBox();
            await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
            await page.mouse.wheel(0, -100);
            await page.waitForFunction(() => document.querySelector('dialog[open] [aria-label="Reset zoom and fit diagram"]').textContent !== '100%');
            const wheeled = await transform();
            assert.ok(wheeled.zoom > before.zoom, 'Wheel up zooms in');
            assert.ok(Math.abs((before.cx - before.x) * wheeled.zoom / before.zoom - (wheeled.cx - wheeled.x)) < 0.2,
              'Wheel zooms around midpoint');
            await page.mouse.wheel(0, 100);
            await page.waitForFunction(() => document.querySelector('dialog[open] [aria-label="Reset zoom and fit diagram"]').textContent === '100%');
            const start = await transform();
            await page.mouse.move(box.x + 40, box.y + 40);
            await page.mouse.down();
            await page.mouse.move(box.x + 100, box.y + 80, {steps: 5});
            await page.mouse.up();
            const panned = await transform();
            assert.ok(Math.abs(panned.x - start.x - 60) < 1, 'Drag pans horizontally');
            assert.ok(Math.abs(panned.y - start.y - 40) < 1, 'Drag pans vertically');
            await viewport.focus();
            await page.keyboard.press('ArrowDown');
            assert.ok(Math.abs((await transform()).y - panned.y + 40) < 1, 'Keyboard pans vertically');
            await zoomIn.click();
            await zoomLevel.click();
            assert.equal(await zoomLevel.textContent(), '100%');
            const reset = await transform();
            assert.ok(Math.abs(reset.x - before.x) < 1 && Math.abs(reset.y - before.y) < 1,
              'Reset recenters the viewport');
            for (const [action, nextAction] of [
              ['Left to right', 'Top to bottom'],
              ['Top to bottom', 'Left to right'],
            ]) {
              await zoomIn.click();
              await dialog.getByRole('button', {name: action}).click();
              assert.equal(await dialog.getByRole('button', {name: nextAction}).count(), 1);
              assert.equal(await zoomLevel.textContent(), '100%');
              await waitForFit(expected);
            }
            if (route.includes('RagSearch') && i === 0) {
              const panelLinks = dialog.getByRole('group', {name: 'Diagrams in this figure'});
              for (const title of ['Indexing before deployment', 'Search and answer generation']) {
                await zoomIn.click();
                const panel = panelLinks.getByRole('button', {name: title, exact: true});
                await panel.click();
                assert.equal(await panel.getAttribute('aria-pressed'), 'true');
                assert.equal(await zoomLevel.textContent(), '100%');
                await waitForFit(1);
                assert.equal(await dialog.locator('.diagram-panel h4:visible').count(), 0);
                assert.equal((await dialog.locator('svg:visible title').textContent()).trim(), title);
              }
              await panelLinks.getByRole('button', {name: 'All diagrams'}).click();
              await waitForFit(expected);
              assert.equal(await dialog.locator('.diagram-panel h4:visible').count(), 2);
            }
            if (width === 1440 && theme === 'light' && route.includes('scaling')) {
              for (let step = 0; step < 20; step++) await zoomIn.evaluate(button => button.click());
              assert.equal(await zoomLevel.textContent(), '400%');
              assert.equal(await zoomIn.isDisabled(), true);
              for (let step = 0; step < 30; step++) await zoomOut.evaluate(button => button.click());
              assert.equal(await zoomLevel.textContent(), '25%');
              assert.equal(await zoomOut.isDisabled(), true);
            }
            const close = dialog.getByRole('button', {name: 'Close', exact: true});
            assert.equal(await close.getAttribute('title'), 'Close (Esc)');
            await viewport.hover({position: {x: 4, y: 4}});
            const buttonChrome = button => button.evaluate(element => {
              const style = getComputedStyle(element);
              return [style.backgroundColor, style.borderColor, style.borderRadius, style.height];
            });
            assert.deepEqual(await buttonChrome(close), await buttonChrome(
              dialog.getByRole('button', {name: /^(Left to right|Top to bottom)$/})));
            if (i === 0) await page.keyboard.press('Escape');
            else await close.click();
            await dialog.waitFor({state: 'hidden'});
            assert.equal(await button.evaluate(element => element === document.activeElement), true, 'Focus returns to opener');
            await page.waitForFunction(count => document.querySelectorAll('figure svg').length === count, count);
            await checkDescriptions(page.locator('figure'), descriptions);
          }
        }
        assert.deepEqual(errors, [], `${route}: browser errors`);
        report.push({route, width, theme, figures: metrics});
        console.log(`${width}px ${theme}: ${route} passed`);
      }
      await context.close();
    }
    if (output) fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
    console.log('All diagram styling, fullscreen, midpoint zoom, wheel and drag checks passed.');
  } finally {await browser.close();}
})().catch(error => {console.error(error); process.exitCode = 1;});
