const assert = require('node:assert/strict');
const os = require('node:os');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.DIAGRAM_BASE_URL || 'http://localhost:3000/docusaurusportfolio';
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
      const cards = page.locator('#case-studies article');
      async function clickCardText(locator, destination) {
        await locator.evaluate(element => element.scrollIntoView({block: 'center'}));
        const box = await locator.boundingBox();
        const x = box.x + 4;
        const y = box.y + 4;
        // The native link overlay intentionally receives clicks above card text.
        const actual = await page.evaluate(({x, y}) => document.elementFromPoint(x, y)?.closest('a')?.getAttribute('href'), {x, y});
        assert.equal(actual, destination);
        await page.mouse.click(x, y);
        await page.waitForURL(url => url.pathname === destination);
      }
      for (let index = 0; index < 4; index++) {
        await page.goto(base + '/');
        const card = cards.nth(index);
        const mainLink = card.getByRole('link', {name: /^Read (case study|documentation sample):/});
        const destination = await mainLink.getAttribute('href');
        // Click blank space inside the card, beyond the actual link text.
        await card.scrollIntoViewIfNeeded();
        const box = await card.boundingBox();
        await page.mouse.click(box.x + box.width - 8, box.y + 8);
        await page.waitForURL(url => url.pathname === destination);
        await page.goto(base + '/');
        await page.keyboard.press('Tab');
        await mainLink.focus();
        const outline = await mainLink.evaluate(element => getComputedStyle(element, '::after').outlineStyle);
        assert.equal(outline, 'solid', 'Keyboard focus outlines the entire card');
        await page.keyboard.press('Enter');
        await page.waitForURL(url => url.pathname === destination);
        await page.goto(base + '/');
        await clickCardText(card.locator('h3'), destination);
        await page.goto(base + '/');
        await clickCardText(card.locator('p[class*="description"]'), destination);
      }
      const independent = [
        [0, 'Morgan Stanley', 'https://www.morganstanley.com/'],
        [1, 'Paysafe', 'https://www.paysafe.com/'],
        [2, 'Mastercard', 'https://www.mastercard.com/'],
        [1, 'public Developer Center', 'https://developer.paysafe.com/en/'],
        [2, 'Apple Pay', 'https://www.apple.com/apple-pay/'],
        [1, 'Skrill', 'https://www.skrill.com/'],
        [1, 'Optimal Payments', 'https://www.paysafe.com/us-en/paysafegroup/news/detail/optimal-payments-becomes-paysafe-in-game-changing-global-rebrand/'],
      ];
      for (const [index, label, url] of independent) {
        // Verify destinations without sending test traffic to third-party sites.
        await page.route(url, route => route.fulfill({contentType: 'text/html', body: '<title>Destination fixture</title>'}));
        await page.goto(base + '/');
        await cards.nth(index).getByRole('link', {name: label, exact: true}).click();
        await page.waitForURL(url);
      }
      console.log(`${width}px ${theme}: card background/title/text, keyboard focus and activation, and independent external links passed`);
      await context.close();
    }
  } finally {await browser.close();}
})().catch(error => {console.error(error); process.exitCode = 1;});
