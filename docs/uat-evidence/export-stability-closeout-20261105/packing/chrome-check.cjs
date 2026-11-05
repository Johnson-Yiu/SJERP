const { chromium } = require('../../../../frontend/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
(async () => {
  const dir = __dirname, results = [];
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
  try {
    await page.goto('http://127.0.0.1:18243/orders?detail=1&tab=packing', {waitUntil: 'domcontentloaded'});
    const button = page.getByRole('button', {name:'导出 Packing List'});
    await button.waitFor({timeout:30000});
    await page.screenshot({path:path.join(dir,'chrome-packing.png')});
    for (let i=0;i<10;i++) {
      try {
        const p = page.waitForEvent('download',{timeout:30000});
        const responsePromise = page.waitForResponse(r => r.url().includes('/export-packing-list/'));
        await button.click();
        const download = await p;
        const filename = path.join(dir,`download-${i+1}.xlsx`);
        await download.saveAs(filename);
        const response = await responsePromise;
        const apiBytes = await response.body(), downloaded = fs.readFileSync(filename);
        results.push({attempt:i+1, filename:download.suggestedFilename(), status:response.status(), contentType:response.headers()['content-type'], bytes:downloaded.length, sha256:crypto.createHash('sha256').update(downloaded).digest('hex'), matchesResponse:apiBytes.equals(downloaded), failure:await download.failure()});
      } catch (error) { results.push({attempt:i+1,error:String(error)}); }
    }
    fs.writeFileSync(path.join(dir,'chrome-results.json'),JSON.stringify({version:browser.version(),url:page.url(),results},null,2));
  } finally { await browser.close(); }
})().catch(e=>{ console.error(e); process.exitCode=1 });
