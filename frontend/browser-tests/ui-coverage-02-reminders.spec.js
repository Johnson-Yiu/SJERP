import {test,expect} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import path from 'node:path'
test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
test('long reminder list new and detail positioning',async({page,browser})=>{
 test.setTimeout(120000)
 const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[];await mkdir(path.join(root,'originals'),{recursive:true})
 async function snap(stage){
  await page.evaluate(()=>document.fonts.ready)
  const info=await page.evaluate(()=>{const e=document.querySelector('.reminders .editor'),r=e?.getBoundingClientRect();let n=document.elementFromPoint(900,650),chain=[];while(n){const s=getComputedStyle(n);if(n.scrollHeight>n.clientHeight+5)chain.push({tag:n.tagName,className:typeof n.className==='string'?n.className:'',scrollTop:n.scrollTop,clientHeight:n.clientHeight,scrollHeight:n.scrollHeight,overflowY:s.overflowY});n=n.parentElement}return {route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,windowScrollY:scrollY,rowCount:document.querySelectorAll('.reminders .requirement').length,editor:r?{x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom}:null,scrollChain:chain}})
  const name=`ULR013-B-${stage}.png`,b=await page.screenshot({path:path.join(root,'originals',name),fullPage:false})
  entries.push({evidence_id:name,surface_id:'G088',expanded_case_id:`ULR013-B-${stage}`,related_ulr:['ULR-013'],source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...info,role:'authenticated codex test superuser',data:'12 synthetic reminders in isolated SQLite; no UI save',simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)}})
  await writeFile(path.join(root,'reminders-manifest.json'),JSON.stringify(entries,null,2))
 }
 async function wheel(delta){await page.mouse.move(900,600);await page.mouse.wheel(0,delta);await page.waitForTimeout(500)}
 await page.goto('/new-product-reminders',{waitUntil:'domcontentloaded'})
 await expect(page.locator('.requirement')).toHaveCount(12)
 await snap('before-new');await page.getByRole('button',{name:'记录新品需求',exact:true}).click()
 await expect(page.locator('.reminders .editor')).toBeAttached();await snap('after-new')
 await wheel(5000);await snap('new-bottom')
 await page.locator('.reminders .editor').getByRole('button',{name:'取消',exact:true}).click()
 await wheel(-5000)
 await page.getByRole('button',{name:/查看需求 #/}).first().click()
 await expect(page.locator('.reminders .editor h3')).toHaveText('新品需求详情')
 await snap('after-detail');await wheel(5000);await snap('detail-bottom')
})
