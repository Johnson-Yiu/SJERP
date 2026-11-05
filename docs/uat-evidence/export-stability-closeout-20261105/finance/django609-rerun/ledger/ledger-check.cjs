const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict'),{createRequire}=require('node:module')
const root=__dirname, setup=JSON.parse(fs.readFileSync(path.join(root,'setup.json'),'utf8').replace(/^\ufeff/,'')),{chromium,expect}=createRequire(path.resolve('frontend/package.json'))('@playwright/test')
const results=[],base=`http://127.0.0.1:${setup.vite_port}`
;(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});try{
for(const width of [1440,390]){
 const page=await browser.newPage({viewport:{width,height:1000},acceptDownloads:true});let mocked=0;const errors=[];page.on('pageerror',e=>errors.push(e.message))
 try{
 await page.route('**/api/finance-ledger/facts/**',async route=>{const u=new URL(route.request().url());if(u.searchParams.get('export')==='csv'&&mocked===0){mocked++;return route.fulfill({status:400,contentType:'application/json',body:JSON.stringify({detail:'合成导出失败，请重试'})})}return route.continue()})
 await page.goto(base+'/finance-ledger');await expect(page.locator('.ledger-page').getByRole('heading',{name:'账户资金'})).toBeVisible();const button=page.getByRole('button',{name:'导出 CSV',exact:true});await expect(button).toBeEnabled()
 await page.getByLabel('开始日期',{exact:true}).fill('2026-09-01');await page.getByLabel('结束日期',{exact:true}).fill('2026-09-30');await page.getByRole('button',{name:'查询',exact:true}).click();await expect(page.locator('.ledger-cards').getByText('=SYNTH-09',{exact:false}).first()).toBeVisible()
 await page.screenshot({path:path.join(root,`ledger-${width}-09.png`),fullPage:true})
 await button.click();await expect(page.getByRole('alert')).toContainText('合成导出失败');await expect(button).toBeEnabled();await page.screenshot({path:path.join(root,`ledger-${width}-failure.png`),fullPage:true})
 for(const month of ['09','10']){
  const from=`2026-${month}-01`,to=`2026-${month}-${month==='09'?'30':'31'}`
  await page.getByLabel('开始日期',{exact:true}).fill(from);await page.getByLabel('结束日期',{exact:true}).fill(to);await page.getByRole('button',{name:'查询',exact:true}).click();await expect(page.locator('.ledger-cards').getByText(`=SYNTH-${month}`,{exact:false}).first()).toBeVisible()
  if(month==='10')await page.screenshot({path:path.join(root,`ledger-${width}-10.png`),fullPage:true})
  for(let iteration=1;iteration<=2;iteration++){
   const rp=page.waitForResponse(r=>{const u=new URL(r.url());return u.pathname==='/api/finance-ledger/facts/'&&u.searchParams.get('export')==='csv'}),dp=page.waitForEvent('download');await button.click();const [response,download]=await Promise.all([rp,dp]);assert.equal(response.status(),200);const browserResponse=await response.body(),bytes=fs.readFileSync(await download.path());const rawResponse=await fetch(response.url());assert.equal(rawResponse.status,200);const raw=Buffer.from(await rawResponse.arrayBuffer());assert.deepEqual(bytes,raw);assert.deepEqual([...bytes.subarray(0,3)],[239,187,191]);const text=bytes.toString('utf8');assert(text.includes('account_name')&&text.includes('source_key'));for(const prefix of ['=','+','-','@'])assert(text.includes("'"+prefix+'SYNTH-'+month),`missing ${prefix} ${month}`);const amount=month==='09'?'120.01':'450.01';assert(text.includes(amount));assert(!text.includes('SYNTH-'+(month==='09'?'10':'09')));const filename=`ledger-${width}-${month}-${iteration}.csv`;fs.writeFileSync(path.join(root,filename),bytes)
   results.push({width,period:[from,to],iteration,responseStatus:response.status(),downloadName:download.suggestedFilename(),file:filename,bytes:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),bom:true,amount,formulaPrefixes:['=','+','-','@'],independentHttpEqualsDownload:true,browserBodyEqualsDownload:browserResponse.equals(bytes),browserBodyEqualsWithoutBom:browserResponse.equals(bytes.subarray(3))});console.log(JSON.stringify(results.at(-1)))
  }
  if(month==='09'){await page.goto(base+'/finance');await page.goto(base+'/finance-ledger');await expect(button).toBeEnabled()}
 }
 assert.equal(mocked,1);assert.deepEqual(errors,[]);const size=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));assert(size.document<=width,JSON.stringify(size));console.log(JSON.stringify({width,mocked400:mocked,pageErrors:errors,size,pageSwitch:true}))
 }catch(e){console.error('FAIL width',width,e);await page.screenshot({path:path.join(root,`ledger-${width}-unexpected-failure.png`),fullPage:true}).catch(()=>{});results.push({width,error:String(e)})}finally{await page.close()}
}
}finally{await browser.close();fs.writeFileSync(path.join(root,'results.json'),JSON.stringify(results,null,2))}if(results.length!==8||results.some(r=>r.error))process.exitCode=1})().catch(e=>{console.error(e);process.exitCode=1})

