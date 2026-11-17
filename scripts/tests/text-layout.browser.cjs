// Uses the existing Playwright/browser environment documented for diagram checks.
const assert = require('node:assert/strict');
const os = require('node:os');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.DIAGRAM_BASE_URL || 'http://localhost:3000/docusaurusportfolio';
const scenarios = [
  {name: 'desktop', width: 1440},
  {name: '200% browser-zoom layout equivalent', width: 640},
  {name: '320px reflow', width: 320},
  {name: '200% text size', width: 1280, rootSize: 32},
  {name: '320px with text-spacing overrides', width: 320, spacing: true},
];
(async () => {
  const browser = await chromium.launch({headless: true,
    executablePath: process.env.CHROMIUM_EXECUTABLE || undefined,
    env: {PATH: process.env.PATH, HOME: os.tmpdir(),
      LD_LIBRARY_PATH: process.env.DIAGRAM_BROWSER_LIBRARY_PATH || ''}});
  try {
    for (const theme of ['light', 'dark']) for (const scenario of scenarios) {
      const context = await browser.newContext({viewport: {width: scenario.width, height: 1000}, colorScheme: theme});
      await context.addInitScript(value => localStorage.setItem('theme', value), theme);
      const page = await context.newPage();
      for (const route of ['', '/explore', '/docs/docs-samples/MDES4Merchants', '/docs/case-studies/scalingdeveloperdocs']) {
        await page.goto(base + route);
        await page.locator('main h1').first().waitFor();
        if (route === '/explore') await page.locator('article').first().waitFor();
        if (scenario.rootSize) await page.addStyleTag({content: `html {font-size: ${scenario.rootSize}px !important}`});
        if (scenario.spacing) await page.addStyleTag({content: `
          main :not(svg):not(svg *) {
            line-height: 1.5 !important;
            letter-spacing: 0.12em !important;
            word-spacing: 0.16em !important;
          }
          main p {margin-bottom: 2em !important;}
        `});
        const metrics = await page.evaluate(() => {
          const root = parseFloat(getComputedStyle(document.documentElement).fontSize);
          const visible = element => element.getBoundingClientRect().width > 0 && element.getBoundingClientRect().height > 0;
          const sizes = selector => [...document.querySelectorAll(selector)].filter(visible).map(element => parseFloat(getComputedStyle(element).fontSize));
          return {root, pageWidth: document.documentElement.scrollWidth, viewport: innerWidth,
            outliers: [...document.querySelectorAll('main *')].filter(visible)
              .filter(element => !element.closest('svg, dialog'))
              .filter(element => element.getBoundingClientRect().right > innerWidth + 1)
              .slice(0, 6).map(element => ({tag: element.tagName, className: element.className, text: element.textContent.slice(0, 50)})),
            body: sizes('main p[class*="description"], main p[class*="lead"], main p[class*="intro"], main p[class*="summary"], .theme-doc-markdown > p'),
            secondary: sizes('[class*="metadataTag"], p[class*="evidenceNote"], [class*="employer"]'),
            clipped: [...document.querySelectorAll('main button, main label, main h1, main h2, main h3, main a')]
              .filter(visible).filter(element => !element.closest('svg, dialog'))
              .filter(element => {
                const s = getComputedStyle(element);
                return ['hidden', 'clip'].includes(s.overflowX) && element.scrollWidth > element.clientWidth + 2;
              }).map(element => element.textContent.trim().slice(0, 80)),
          };
        });
        assert.ok(metrics.pageWidth <= metrics.viewport + 1, `${scenario.name} ${route}: page overflow ${JSON.stringify(metrics)}`);
        assert.deepEqual(metrics.clipped, [], `${scenario.name} ${route}: clipped controls/headings`);
        assert.ok(metrics.body.length && metrics.body.every(size => Math.abs(size - metrics.root) < 0.1), `${route}: body sizes ${metrics.body}`);
        assert.ok(metrics.secondary.every(size => Math.abs(size - metrics.root * 0.875) < 0.1), `${route}: secondary sizes ${metrics.secondary}`);
      }
      // Check the Search reading text using a local saved-result fixture.
      await page.goto(`${base}/explore?view=ai-search`);
      await page.locator('#explore-ai-panel form').waitFor();
      await page.evaluate(() => {
        const key = 'governed-rag-search:v1';
        const saved = JSON.parse(sessionStorage.getItem(key));
        Object.assign(saved, {hasSearched: true, responseMode: 'search', items: [{title: 'Readable source passage', url: '/docs/example', text: 'Body text should use the same readable size throughout the site.'}]});
        sessionStorage.setItem(key, JSON.stringify(saved));
      });
      await page.reload();
      const search = page.locator('#explore-ai-panel');
      await search.locator('article').waitFor();
      if (scenario.rootSize) await page.addStyleTag({content: `html {font-size:${scenario.rootSize}px !important}`});
      if (scenario.spacing) await page.addStyleTag({content: 'main :not(svg):not(svg *) {line-height:1.5 !important;letter-spacing:.12em !important;word-spacing:.16em !important} main p {margin-bottom:2em !important}'});
      const preview = search.locator('[class*="snippetPreview"]');
      const bodySize = await preview.evaluate(element => getComputedStyle(element).fontSize);
      assert.equal(bodySize, `${scenario.rootSize || 16}px`);
      await preview.click();
      assert.equal(await search.locator('[class*="fullPassage"]').evaluate(element => getComputedStyle(element).fontSize), bodySize);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, `Search: ${scenario.name}`);
      console.log(`${theme}: ${scenario.name} — body/secondary sizes, reflow and text clipping passed`);
      await context.close();
    }
  } finally {await browser.close();}
})().catch(error => {console.error(error); process.exitCode = 1;});
