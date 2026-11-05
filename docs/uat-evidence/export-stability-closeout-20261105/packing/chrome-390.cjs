const { chromium } = require('../../../../frontend/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

(async () => {
  const dir = __dirname;
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, acceptDownloads: true });
  try {
    await page.goto('http://127.0.0.1:18243/orders?detail=1&tab=packing', { waitUntil: 'domcontentloaded' });
    const button = page.getByRole('button', { name: '导出 Packing List' });
    await button.waitFor({ timeout: 30000 });
    if (!await button.isEnabled()) throw new Error('Packing List export button is disabled');
    await button.scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(dir, 'chrome-packing-390.png') });
    const responsePromise = page.waitForResponse(r => r.url().includes('/export-packing-list/'));
    const downloadPromise = page.waitForEvent('download', { timeout: 30000 });
    await button.click();
    const download = await downloadPromise;
    const destination = path.join(dir, 'download-390.xlsx');
    await download.saveAs(destination);
    const response = await responsePromise;
    const body = await response.body(), file = fs.readFileSync(destination);
    const result = { chrome: browser.version(), url: page.url(), viewport: page.viewportSize(), filename: download.suggestedFilename(), status: response.status(), contentType: response.headers()['content-type'], bytes: file.length, sha256: crypto.createHash('sha256').update(file).digest('hex'), matchesResponse: body.equals(file), failure: await download.failure() };
    console.log(JSON.stringify(result, null, 2));
    fs.writeFileSync(path.join(dir, 'chrome-results-390.json'), JSON.stringify(result, null, 2) + '\n');
    if (result.status !== 200 || result.failure || !result.matchesResponse || !file.length) throw new Error('Download validation failed');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
