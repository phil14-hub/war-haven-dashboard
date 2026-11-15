import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createServer} from 'node:http';
import {chromium} from 'playwright';

const password = process.env.DASHBOARD_PASSWORD;
if (!password) throw Error('A configured dashboard passphrase is required for the smoke test.');
const html = await readFile(process.argv[2]);
const server = createServer((request, response) => {
  if (request.url?.split('?')[0] !== '/') {
    response.writeHead(404).end();
    return;
  }
  response.writeHead(200, {'Content-Type': 'text/html; charset=utf-8'}).end(html);
});
await new Promise((resolve, reject) => server.once('error', reject).listen(0, '127.0.0.1', resolve));
let browser;
try {
  const origin = `http://127.0.0.1:${server.address().port}`;
  browser = await chromium.launch();
  for (const viewport of [{width: 1280, height: 860}, {width: 390, height: 844}]) {
    const page = await browser.newPage({viewport});
    await page.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
    try {
      await page.goto(origin + '/?legacy=1');
      assert.equal(await page.locator('.account-signin').count(), 1);
      const form = page.locator('#unlock-form');
      const field = form.locator('#dashboard-password');
      const unlock = form.locator('#unlock-button');
      await field.fill('deliberately invalid staging passphrase');
      await unlock.click();
      await page.waitForFunction(() => /passphrase is incorrect/i.test(document.getElementById('unlock-error')?.textContent ?? ''));
      assert.equal(await page.locator('#war-data').count(), 0);
      await field.fill(password);
      await unlock.click();
      await page.waitForFunction(() => Boolean(document.getElementById('war-data')) && !document.getElementById('unlock-form'));
      const validClan = await page.locator('#war-data').evaluate(script => {
        const data = JSON.parse(script.textContent);
        return data.clanTag === '#2PQQJ0GR0' && Array.isArray(data.roster) && data.roster.length > 0;
      });
      assert.equal(validClan, true, 'Expected the saved War Haven dashboard to open.');
    } catch {
      // Never print browser diagnostics that might include a secret or decrypted records.
      throw Error(`The Pages unlock smoke test failed at ${viewport.width}px.`);
    } finally {
      await page.close();
    }
  }
  console.log('The staged Pages page rejected an incorrect passphrase and opened with the configured passphrase at desktop and phone widths.');
} finally {
  await browser?.close();
  await new Promise(resolve => server.close(resolve));
}
