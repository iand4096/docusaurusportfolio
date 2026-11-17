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

(async () => {
  if (output) fs.mkdirSync(output, {recursive: true});
  const browser = await chromium.launch({headless: true,
    executablePath: process.env.CHROMIUM_EXECUTABLE || undefined,
    env: {PATH: process.env.PATH, HOME: os.tmpdir(),
      LD_LIBRARY_PATH: process.env.DIAGRAM_BROWSER_LIBRARY_PATH || ''}});
  const report = [];
  try {
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
            assert.equal(await dialog.getByRole('list', {name: 'Colour and icon key'}).count(), 1);
            if (output) await page.screenshot({path: path.join(output, `${route.split('/').pop()}-${i}-${width}-${theme}-fullscreen.png`)});
            const viewport = dialog.getByLabel(/^Diagram viewport:/);
            const zoomLevel = dialog.getByLabel('Zoom level', {exact: true});
            const zoomIn = dialog.getByRole('button', {name: 'Zoom in', exact: true});
            const zoomOut = dialog.getByRole('button', {name: 'Zoom out', exact: true});
            assert.match(await zoomIn.getAttribute('title'), /mouse wheel/);
            assert.match(await zoomOut.getAttribute('title'), /mouse wheel/);
            assert.equal(await zoomLevel.textContent(), '100%');
            const transform = () => viewport.evaluate(element => {
              const matrix = new DOMMatrix(getComputedStyle(element.firstElementChild).transform);
              return {zoom: matrix.a, x: matrix.e, y: matrix.f,
                cx: element.clientWidth / 2, cy: element.clientHeight / 2};
            });
            const before = await transform();
            await zoomIn.click();
            assert.equal(await zoomLevel.textContent(), '120%');
            const after = await transform();
            assert.ok(Math.abs((before.cx - before.x) / before.zoom - (after.cx - after.x) / after.zoom) < 0.01,
              'Zoom keeps the horizontal midpoint fixed');
            assert.ok(Math.abs((before.cy - before.y) / before.zoom - (after.cy - after.y) / after.zoom) < 0.01,
              'Zoom keeps the vertical midpoint fixed');
            await zoomOut.click();
            assert.equal(await zoomLevel.textContent(), '100%');
            const box = await viewport.boundingBox();
            await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
            await page.mouse.wheel(0, -100);
            await page.waitForFunction(() => document.querySelector('dialog[open] output').textContent !== '100%');
            const wheeled = await transform();
            assert.ok(wheeled.zoom > 1, 'Wheel up zooms in');
            assert.ok(Math.abs((wheeled.cx - wheeled.x) / wheeled.zoom - before.cx) < 0.01, 'Wheel zooms around midpoint');
            await page.mouse.wheel(0, 100);
            await page.waitForFunction(() => document.querySelector('dialog[open] output').textContent === '100%');
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
            if (width === 1440 && theme === 'light' && route.includes('scaling')) {
              for (let step = 0; step < 20; step++) await zoomIn.evaluate(button => button.click());
              assert.equal(await zoomLevel.textContent(), '400%');
              assert.equal(await zoomIn.isDisabled(), true);
              for (let step = 0; step < 30; step++) await zoomOut.evaluate(button => button.click());
              assert.equal(await zoomLevel.textContent(), '25%');
              assert.equal(await zoomOut.isDisabled(), true);
            }
            if (i === 0) await page.keyboard.press('Escape');
            else await dialog.getByRole('button', {name: 'Close', exact: true}).click();
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
