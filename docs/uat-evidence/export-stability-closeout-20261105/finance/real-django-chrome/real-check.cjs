const { createRequire } = require('node:module')
const path = require('node:path'), fs = require('node:fs'), assert = require('node:assert/strict'), crypto = require('node:crypto')
const requireFrontend = createRequire(path.resolve(process.cwd(), 'frontend/package.json'))
const { chromium } = requireFrontend('@playwright/test')
const output = __dirname
const summary = []
;(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true})
 try {
 for(const width of [1440,390]) {
  const page=await browser.newPage({viewport:{width,height:900},acceptDownloads:true})
  for(const [month,amount] of [['09','122.01'],['10','450.01']]) {
   const from=`2026-${month}-01`,to=`2026-${month}-${month==='09'?'30':'31'}`
   await page.goto(`http://127.0.0.1:5299/finance?date_from=${from}&date_to=${to}`)
   await page.getByRole('button',{name:'导出 CSV',exact:true}).waitFor({state:'visible'})
   await page.getByRole('button',{name:'导出实际资金 CSV',exact:true}).waitFor({state:'visible'})
   await page.screenshot({path:path.join(output,`screen-${width}-${month}.png`),fullPage:true})
   for(const [kind,button,endpoint] of [['book','导出 CSV','/api/finance-dashboard/'],['actual','导出实际资金 CSV','/api/actual-rmb-cash/']]) {
    for(let n=1;n<=2;n++) {
     const responseP=page.waitForResponse(r=>{const u=new URL(r.url());return u.pathname===endpoint && u.searchParams.get('export')==='csv'})
     const downloadP=page.waitForEvent('download')
     await page.getByRole('button',{name:button,exact:true}).click()
     const [response,download]=await Promise.all([responseP,downloadP]);assert.equal(response.status(),200)
     const responseBytes=await response.body(),downloadBytes=fs.readFileSync(await download.path())
     const raw=Buffer.from(await (await fetch(response.url())).arrayBuffer()); assert.deepEqual(downloadBytes,raw); assert(responseBytes.equals(raw) || responseBytes.equals(raw.subarray(3))); assert.deepEqual([...downloadBytes.subarray(0,3)],[239,187,191])
     const content=downloadBytes.toString('utf8');assert(content.includes(amount),`missing amount ${amount}`);for(const prefix of ["=","+","-","@"]) assert(content.includes("'"+prefix+"synthetic"),`missing escaped formula ${prefix}`)
     const name=`${width}-${month}-${kind}-${n}.csv`;fs.writeFileSync(path.join(output,name),downloadBytes)
     summary.push({width,period:[from,to],kind,iteration:n,status:response.status(),contentType:response.headers()['content-type'],downloadName:download.suggestedFilename(),bytes:downloadBytes.length,sha256:crypto.createHash('sha256').update(downloadBytes).digest('hex'),rawHttpEqualsDownload:true,browserResponseEqualsDownload:responseBytes.equals(downloadBytes),browserResponseEqualsDownloadWithoutBom:responseBytes.equals(downloadBytes.subarray(3)),bom:true,amount,formulaPrefixes:["=","+","-","@"]})
    }
   }
  }
  await page.close()
 }
 } finally {await browser.close();fs.writeFileSync(path.join(output,'results.json'),JSON.stringify(summary,null,2))}
 console.log(`PASS ${summary.length} real HTTP / Chrome downloads`)
})().catch(e=>{console.error(e);process.exitCode=1})



