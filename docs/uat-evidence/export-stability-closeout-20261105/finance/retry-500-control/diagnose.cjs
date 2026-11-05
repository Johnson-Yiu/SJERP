const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{createRequire}=require('node:module')
const root=__dirname,setup=JSON.parse(fs.readFileSync(path.join(root,'setup.json'),'utf8').replace(/^\ufeff/,'')),{chromium,expect}=createRequire(path.resolve('frontend/package.json'))('@playwright/test')
const events=[],start=Date.now(),log=(event,extra={})=>{const row={elapsedMs:Date.now()-start,event,...extra};events.push(row);console.log(JSON.stringify(row))};let attempts=0,browser,page,manual=false
;(async()=>{try{
 browser=await chromium.launch({channel:'chrome',headless:true});page=await browser.newPage({viewport:{width:1440,height:900},acceptDownloads:true});log('browser',{version:browser.version()})
 await page.route('**/api/**',async route=>{const u=new URL(route.request().url()),period={date_from:u.searchParams.get('date_from'),date_to:u.searchParams.get('date_to')};
 if(u.pathname.includes('current-operator'))return route.fulfill({json:{authenticated:true,development_superadmin:true,has_all_permissions:true}})
 if(u.pathname==='/api/finance-dashboard/'){
  if(u.searchParams.get('export')==='csv'){attempts++;const status=manual?200:500;log('export-request',{attempt:attempts,status,manual,query:u.search});return status===500?route.fulfill({status:500,contentType:'application/json',body:'{"detail":"synthetic 500"}'}):route.fulfill({status:200,contentType:'text/csv; charset=utf-8',body:'\ufeff期间,金额\r\n2026-10-01,42.00\r\n'})}
  return route.fulfill({json:{period,metrics:{},due_items:[],monthly_cash:[],categories:[]}})}
 if(u.pathname==='/api/actual-rmb-cash/')return route.fulfill({json:{basis:'bank_cash_confirmed_v1',period,totals:{inflow:'0',outflow:'0',net:'0',count:0},monthly:[],by_kind:[],events:[]}})
 return route.fulfill({json:[]})})
 await page.goto(`http://127.0.0.1:${setup.port}/finance?date_from=2026-10-01&date_to=2026-10-19`)
 const button=page.getByRole('button',{name:'导出 CSV',exact:true});await expect(button).toBeEnabled();await page.screenshot({path:path.join(root,'before.png'),fullPage:true});log('click-first')
 await button.click();await expect(page.getByRole('button',{name:'正在导出…'})).toBeDisabled();log('pending-disabled')
 await expect(page.getByRole('alert')).toContainText('服务器暂时不可用',{timeout:30000});await expect(button).toBeEnabled();assert.equal(attempts,6,'initial request plus five automatic retries');log('exhausted',{attempts,error:await page.getByRole('alert').innerText(),buttonEnabled:await button.isEnabled()});await page.screenshot({path:path.join(root,'failure-exhausted.png'),fullPage:true})
 manual=true;const downloadP=page.waitForEvent('download',{timeout:15000});log('click-manual');await button.click();const download=await downloadP,bytes=fs.readFileSync(await download.path());assert.equal(attempts,7);assert.deepEqual([...bytes.subarray(0,3)],[239,187,191]);assert(bytes.toString().includes('2026-10-01,42.00'));await expect(page.getByRole('status')).toContainText('CSV 已开始下载');await expect(button).toBeEnabled();await expect(page.getByRole('alert')).toHaveCount(0)
 fs.writeFileSync(path.join(root,'retry-success.csv'),bytes);log('download',{attempts,filename:download.suggestedFilename(),bytes:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),bom:true});await page.screenshot({path:path.join(root,'success.png'),fullPage:true});log('PASS')
 }catch(e){log('FAIL',{error:String(e),stack:e.stack});if(page)await page.screenshot({path:path.join(root,'unexpected-failure.png'),fullPage:true}).catch(()=>{});process.exitCode=1}finally{fs.writeFileSync(path.join(root,'events.json'),JSON.stringify(events,null,2));if(browser)await browser.close()}})()
