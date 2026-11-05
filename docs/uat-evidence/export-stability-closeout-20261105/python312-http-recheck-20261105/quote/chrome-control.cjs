const { chromium } = require('../../../../../frontend/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { performance } = require('perf_hooks');
const dir = __dirname;
const fixture = JSON.parse(fs.readFileSync(path.join(dir, 'fixture.json')));
const now = () => Number(performance.now().toFixed(2));
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
(async () => {
  const events = [], start = now();
  const mark = (name, extra = {}) => { const event = {name, elapsed_ms: Number((now()-start).toFixed(2)), ...extra}; events.push(event); console.log(JSON.stringify(event)); };
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, acceptDownloads: true });
  try {
    mark('browser_started', {version: browser.version(), userAgent: await page.evaluate(() => navigator.userAgent)});
    await page.goto(`http://127.0.0.1:18463/quotes?detail=${fixture.quote_id}`, {waitUntil:'domcontentloaded'});
    const button = page.getByRole('button', {name:'导出 Excel', exact:true});
    await button.waitFor({timeout:30000});
    await page.screenshot({path:path.join(dir,'quote-page.png')});
    mark('ready');
    const responsePromise = page.waitForResponse(r => new URL(r.url()).pathname === `/api/quotes/${fixture.quote_id}/export/`).then(r => {mark('response_headers', {status:r.status(), contentType:r.headers()['content-type']}); return r;});
    const downloadPromise = page.waitForEvent('download', {timeout:30000}).then(d => {mark('download_event', {suggestedFilename:d.suggestedFilename()}); return d;});
    mark('click_started');
    await button.click();
    mark('click_completed');
    const response = await responsePromise;
    const download = await downloadPromise;
    const internalPath = await download.path();
    mark('download_path_resolved', {internalPath, internalPathLength:internalPath.length});
    const destination = path.join(dir,'browser-download.xlsx');
    await download.saveAs(destination);
    mark('saveAs_completed', {saveAsPath:destination, saveAsPathLength:destination.length, failure:await download.failure()});
    const body = await response.body();
    mark('response_body_read', {bytes:body.length});
    fs.writeFileSync(path.join(dir,'http-response.xlsx'),body);
    const file = fs.readFileSync(destination);
    const result = {version:browser.version(), status:response.status(), contentType:response.headers()['content-type'], contentDisposition:response.headers()['content-disposition'], suggestedFilename:download.suggestedFilename(), internalPath, internalPathLength:internalPath.length, saveAsPath:destination, saveAsPathLength:destination.length, responseBytes:body.length, downloadBytes:file.length, responseSha256:sha(body), downloadSha256:sha(file), exactMatch:body.equals(file), failure:await download.failure(), events};
    fs.writeFileSync(path.join(dir,'browser-result.json'),JSON.stringify(result,null,2)+'\n');
    console.log(JSON.stringify(result,null,2));
    if (result.status !== 200 || result.failure || !result.exactMatch || !body.length || result.suggestedFilename !== `${fixture.quote_no}.xlsx`) throw new Error('HTTP/download validation failed');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1});

