// Run against a local preview using the same browser settings as diagram-figure.browser.cjs.
const assert = require('node:assert/strict');
const os = require('node:os');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.DIAGRAM_BASE_URL || 'http://localhost:3000/docusaurusportfolio';

async function checkContrast(locator, description) {
  const ratios = await locator.evaluateAll(elements => {
    const rgb = value => value.match(/[\d.]+/g).map(Number);
    const luminance = values => values.slice(0, 3).map(value => {
      const channel = value / 255;
      return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
    }).reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
    function background(element) {
      const values = rgb(getComputedStyle(element).backgroundColor);
      const alpha = values[3] ?? 1;
      if (alpha === 1 || !element.parentElement) return values;
      const parent = background(element.parentElement);
      return values.slice(0, 3).map((value, index) => value * alpha + parent[index] * (1 - alpha));
    }
    return elements.map(element => {
      const foreground = luminance(rgb(getComputedStyle(element).color));
      const surface = luminance(background(element));
      return (Math.max(foreground, surface) + 0.05) / (Math.min(foreground, surface) + 0.05);
    });
  });
  assert.ok(ratios.length, `${description}: controls exist`);
  assert.ok(ratios.every(ratio => ratio >= 4.5), `${description}: ${ratios.map(n => n.toFixed(2)).join(', ')} must be >= 4.5`);
  return Math.min(...ratios).toFixed(2);
}

async function checkToggle(page, panel, id) {
  const groups = page.locator(`#${id}`);
  const toggle = panel.getByRole('button', {name: /^(Show|Hide) filters/});
  // Start closed, irrespective of the shared preference from the other tab.
  if (await toggle.getAttribute('aria-expanded') === 'true') await toggle.click();
  assert.equal(await toggle.getAttribute('aria-controls'), id);
  assert.equal(await groups.isVisible(), false);
  assert.equal(await groups.getByRole('button').count(), 0, 'Hidden filters are absent from the accessibility tree');
  await toggle.focus();
  await page.keyboard.press('Enter');
  assert.equal(await toggle.getAttribute('aria-expanded'), 'true');
  assert.equal(await groups.isVisible(), true);
  const chip = groups.locator('button[aria-pressed]').first();
  await chip.focus();
  await page.keyboard.press('Space');
  assert.equal(await chip.getAttribute('aria-pressed'), 'true');
  const selected = groups.getByRole('button', {pressed: true});
  await checkContrast(selected, 'Selected taxonomy chip');
  await checkContrast(selected.locator('span'), 'Selected chip text and count');
  await toggle.focus();
  await page.keyboard.press('Space');
  assert.equal(await toggle.getAttribute('aria-expanded'), 'false');
  assert.equal(await groups.isVisible(), false);
  await toggle.click();
  assert.equal(await chip.getAttribute('aria-pressed'), 'true', 'Toggling visibility retains selections');
  await panel.getByRole('button', {name: 'Clear filters', exact: true}).first().click();
  assert.equal(await panel.getByRole('button', {name: 'Clear filters', exact: true}).count(), 0);
}

(async () => {
  const browser = await chromium.launch({headless: true,
    executablePath: process.env.CHROMIUM_EXECUTABLE || undefined,
    env: {PATH: process.env.PATH, HOME: os.tmpdir(),
      LD_LIBRARY_PATH: process.env.DIAGRAM_BROWSER_LIBRARY_PATH || ''}});
  try {
    for (const width of [1440, 390]) for (const theme of ['light', 'dark']) {
      const context = await browser.newContext({viewport: {width, height: 1000}, colorScheme: theme});
      await context.addInitScript(value => localStorage.setItem('theme', value), theme);
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(`${base}/browse`);
      await page.waitForURL(/\/explore\?/);
      const browse = page.locator('#explore-browse-panel');
      await browse.locator('article').first().waitFor();
      const tabContrast = await checkContrast(page.getByRole('tab', {selected: true}), 'Selected Browse tab');
      await checkToggle(page, browse, 'browse-taxonomy-filters');
      const status = browse.getByRole('status');
      assert.equal(await status.getAttribute('aria-live'), 'polite');
      assert.equal(await status.getAttribute('aria-atomic'), 'true');
      assert.match(await status.textContent(), /\d+ results?/);
      assert.equal(await status.locator('article, a').count(), 0, 'Live count contains no cards or links');
      assert.equal(await browse.locator('section[aria-live]').count(), 0);
      const links = browse.getByRole('link', {name: /^Open content:/});
      assert.equal(await links.count(), await browse.locator('article').count());
      for (const card of await browse.locator('article').all()) {
        assert.equal(await card.getByRole('link', {name: /^Open content:/}).getAttribute('aria-label'),
          `Open content: ${await card.locator('h2').textContent()}`);
      }
      await page.locator('#taxonomy-search').fill('zzznomatchingdocumentzzz');
      assert.match(await status.textContent(), /0 results/);
      await page.locator('#taxonomy-search').fill('');

      // Verify tab keyboard navigation and the same filter behavior in Search.
      await page.getByRole('tab', {name: 'Browse', exact: true}).focus();
      await page.keyboard.press('End');
      const searchTab = page.getByRole('tab', {name: 'Search', exact: true});
      assert.equal(await searchTab.getAttribute('aria-selected'), 'true');
      await checkContrast(searchTab, 'Selected Search tab');
      const search = page.locator('#explore-ai-panel');
      await checkToggle(page, search, 'rag-taxonomy-filters');
      await checkContrast(search.locator('label').filter({has: page.locator('input[type="radio"]:checked')}), 'Selected Search options');
      const primary = search.locator('.button--primary');
      const primaryContrast = await checkContrast(primary, 'Primary Search action');

      // Use a saved local result fixture so no remote API or model is needed.
      await page.evaluate(() => {
        const key = 'governed-rag-search:v1';
        const saved = JSON.parse(sessionStorage.getItem(key));
        Object.assign(saved, {hasSearched: true, responseMode: 'search', items: [{
          title: 'Accessibility fixture document', heading: 'Fixture section',
          url: '/docs/example', text: 'A short source passage.',
        }]});
        sessionStorage.setItem(key, JSON.stringify(saved));
      });
      await page.reload();
      await search.getByRole('region', {name: 'Search results', exact: true}).waitFor();
      const results = search.getByRole('region', {name: 'Search results', exact: true});
      assert.equal(await results.getAttribute('aria-live'), null);
      assert.match(await search.getByRole('status').first().textContent(), /1 result found/);
      assert.equal(await search.getByRole('status').first().locator('article, a').count(), 0);
      assert.equal(await results.getByRole('link', {name: 'Open matched section: Fixture section — Accessibility fixture document'}).count(), 1);
      await page.getByRole('tab', {name: 'Search', exact: true}).focus();
      await page.keyboard.press('Home');
      assert.equal(await page.getByRole('tab', {name: 'Browse', exact: true}).getAttribute('aria-selected'), 'true');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);

      await page.goto(`${base}/docs/docs-samples/MDES4Merchants`);
      await page.getByRole('heading', {name: /^Project overview/, level: 2}).waitFor();
      assert.equal(await page.getByRole('heading', {name: /^Project overview/, level: 3}).count(), 0);
      await page.goto(`${base}/docs/case-studies/scalingdeveloperdocs`);
      // Mermaid renders after hydration; wait before clicking an SSR button.
      await page.locator('figure svg').first().waitFor();
      await page.getByRole('button', {name: /^View full-screen:/}).click();
      const dialog = page.getByRole('dialog');
      const viewport = dialog.getByRole('region', {name: /^Diagram viewport:/});
      assert.equal(await viewport.getAttribute('tabindex'), '0');
      await viewport.focus();
      await page.keyboard.press('Escape');
      await dialog.waitFor({state: 'hidden'});
      assert.deepEqual(errors, []);
      console.log(`${width}px ${theme}: selected tab ${tabContrast}:1, primary action ${primaryContrast}:1; keyboard filters, concise statuses, contextual links, H2 and named diagram region passed`);
      await context.close();
    }
  } finally {await browser.close();}
})().catch(error => {console.error(error); process.exitCode = 1;});
